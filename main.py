from fastapi import FastAPI, File, UploadFile, Query, HTTPException, Form, status as fastapi_status, Request
from fastapi.responses import StreamingResponse, JSONResponse, Response
from pydantic import BaseModel
from typing import Optional
import requests
from io import BytesIO
from PIL import Image
import numpy as np
import uvicorn
from rembg import remove
import cv2
from PIL import ImageFilter
import base64

app = FastAPI()

class ImageUrlRequest(BaseModel):
    url: str

def get_bounding_box(mask: Image.Image):
    # Convert mask to numpy array
    mask_np = np.array(mask)
    # Threshold to binary
    _, thresh = cv2.threshold(mask_np, 127, 255, cv2.THRESH_BINARY)
    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    # Get largest contour
    largest = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(largest)
    return [int(x), int(y), int(x + w), int(y + h)]

def image_to_base64(img: Image.Image) -> str:
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")

@app.post("/remove-background")
async def remove_background(
    request: Request,
    mode: str = Query("fg-image", enum=["fg-image", "fg-mask", "fg-image-shadow"]),
    response_type: str = Query("json", enum=["json", "file"])
):
    # Parse form data manually to avoid FastAPI's automatic parsing
    form_data = await request.form()
    
    # Extract values from form data
    file = form_data.get("file")
    url = form_data.get("url")
    background_url = form_data.get("background_url")
    background_file = form_data.get("background_file")
    
    # Load image from file or URL
    image_bytes = None
    
    # Handle file upload - check if it's a valid file, not empty string
    if file is not None and hasattr(file, 'filename') and file.filename and file.filename.strip():
        try:
            image_bytes = await file.read()
        except Exception as e:
            return JSONResponse({
                "status": "error",
                "message": f"Error reading uploaded file: {str(e)}"
            }, status_code=fastapi_status.HTTP_400_BAD_REQUEST)
    elif url is not None and url.strip():
        try:
            response = requests.get(url)
            if response.status_code != 200:
                return JSONResponse({
                    "status": "error",
                    "message": "Failed to fetch image from URL."
                }, status_code=fastapi_status.HTTP_400_BAD_REQUEST)
            image_bytes = response.content
        except Exception as e:
            return JSONResponse({
                "status": "error",
                "message": f"Error fetching image from URL: {str(e)}"
            }, status_code=fastapi_status.HTTP_400_BAD_REQUEST)
    
    if not image_bytes:
        return JSONResponse({
            "status": "error",
            "message": "No valid image provided. Please provide either a file upload or a valid URL."
        }, status_code=fastapi_status.HTTP_400_BAD_REQUEST)

    try:
        image = Image.open(BytesIO(image_bytes)).convert("RGBA")
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "message": f"Invalid image format: {str(e)}"
        }, status_code=fastapi_status.HTTP_400_BAD_REQUEST)

    # Background removal using rembg
    result = remove(image)
    alpha = result.split()[-1]
    bbox = get_bounding_box(alpha)

    # Prepare background if provided (completely optional)
    background = None
    if background_file is not None and hasattr(background_file, 'filename') and background_file.filename and background_file.filename.strip():
        try:
            bg_bytes = await background_file.read()
            background = Image.open(BytesIO(bg_bytes)).convert("RGBA").resize(result.size)
        except Exception as e:
            return JSONResponse({
                "status": "error",
                "message": f"Invalid background image file: {str(e)}"
            }, status_code=fastapi_status.HTTP_400_BAD_REQUEST)
    elif background_url is not None and background_url.strip():
        try:
            bg_response = requests.get(background_url)
            if bg_response.status_code == 200:
                background = Image.open(BytesIO(bg_response.content)).convert("RGBA").resize(result.size)
            else:
                return JSONResponse({
                    "status": "error",
                    "message": "Failed to fetch background image from URL."
                }, status_code=fastapi_status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return JSONResponse({
                "status": "error",
                "message": f"Error processing background URL: {str(e)}"
            }, status_code=fastapi_status.HTTP_400_BAD_REQUEST)

    # Process based on mode
    if mode == "fg-image":
        output_image = result
        # Only apply background if one was provided
        if background:
            output_image = Image.alpha_composite(background, output_image)
        width, height = output_image.size
        if response_type == "file":
            output_bytes = BytesIO()
            output_image.save(output_bytes, format="PNG")
            output_bytes.seek(0)
            headers = {
                "X-Bounding-Box": str(bbox) if bbox else "None",
                "X-Image-Width": str(width),
                "X-Image-Height": str(height)
            }
            return StreamingResponse(output_bytes, media_type="image/png", headers=headers)
        else:
            image_b64 = image_to_base64(output_image)
            return JSONResponse({
                "status": "success",
                "bounding_box": bbox,
                "image_base64": image_b64,
                "image_size": {"width": width, "height": height}
            })
    elif mode == "fg-mask":
        mask = Image.fromarray(np.array(alpha), mode="L")
        width, height = mask.size
        if response_type == "file":
            output_bytes = BytesIO()
            mask.save(output_bytes, format="PNG")
            output_bytes.seek(0)
            headers = {
                "X-Bounding-Box": str(bbox) if bbox else "None",
                "X-Image-Width": str(width),
                "X-Image-Height": str(height)
            }
            return StreamingResponse(output_bytes, media_type="image/png", headers=headers)
        else:
            image_b64 = image_to_base64(mask)
            return JSONResponse({
                "status": "success",
                "bounding_box": bbox,
                "image_base64": image_b64,
                "image_size": {"width": width, "height": height}
            })
    elif mode == "fg-image-shadow":
        shadow_offset = (10, 10)
        shadow_blur = 15
        shadow_alpha = alpha.copy().filter(ImageFilter.GaussianBlur(radius=shadow_blur))
        shadow = Image.new("RGBA", result.size, (0, 0, 0, 0))
        shadow.paste((0, 0, 0, 100), box=shadow_offset, mask=shadow_alpha)
        shadowed = Image.alpha_composite(shadow, result)
        output_image = shadowed
        # Only apply background if one was provided
        if background:
            output_image = Image.alpha_composite(background, output_image)
        width, height = output_image.size
        if response_type == "file":
            output_bytes = BytesIO()
            output_image.save(output_bytes, format="PNG")
            output_bytes.seek(0)
            headers = {
                "X-Bounding-Box": str(bbox) if bbox else "None",
                "X-Image-Width": str(width),
                "X-Image-Height": str(height)
            }
            return StreamingResponse(output_bytes, media_type="image/png", headers=headers)
        else:
            image_b64 = image_to_base64(output_image)
            return JSONResponse({
                "status": "success",
                "bounding_box": bbox,
                "image_base64": image_b64,
                "image_size": {"width": width, "height": height}
            })
    else:
        return JSONResponse({
            "status": "error",
            "message": "Invalid mode."
        }, status_code=fastapi_status.HTTP_400_BAD_REQUEST)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 