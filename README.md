# Background Remover API

[![Olaverse API](https://img.shields.io/badge/Olaverse-API%20Doc-blue?style=flat-square)](https://www.olaverse.co.uk/background-remover-api) [![Try on Vibeland](https://img.shields.io/badge/Vibeland-Try%20Live-orange?style=flat-square)](https://www.vibeland.co.uk/tools/background-remover)

A FastAPI-based service to remove backgrounds from images, return bounding boxes, and optionally blend with a new background. Supports file upload and URL input for both foreground and background images.

## Features
- Removes background from images (file upload or URL)
- Returns bounding box coordinates of the foreground object
- Returns either:
  - Foreground object with transparent background (RGBA PNG)
  - Foreground mask (grayscale PNG)
  - Foreground with shadow (RGBA PNG)
- Optionally blends result with a new background (file or URL)
- Flexible output: JSON (base64) or direct image file

## API Endpoint

### `POST /remove-background`

#### Query Parameters
- `mode`: Output format (default: `fg-image`)
  - `fg-image`: Foreground object with transparent background
  - `fg-mask`: Grayscale mask of foreground
  - `fg-image-shadow`: Foreground with shadow
- `response_type`: Response format (default: `json`)
  - `json`: JSON with base64 image
  - `file`: Direct PNG image file

#### Form Fields
- `file`: Foreground image file (optional if `url` is provided)
- `url`: URL to foreground image (optional if `file` is provided)
- `background_file`: Background image file (optional)
- `background_url`: URL to background image (optional)

#### Example Request (cURL)
**File Upload:**
```bash
curl -X POST "http://localhost:8000/remove-background?mode=fg-image&response_type=json" \
  -F "file=@input.png"
```

**URL Input:**
```bash
curl -X POST "http://localhost:8000/remove-background?mode=fg-image&response_type=json" \
  -F "url=https://example.com/image.png"
```

**With Background File:**
```bash
curl -X POST "http://localhost:8000/remove-background?mode=fg-image&response_type=json" \
  -F "file=@input.png" -F "background_file=@bg.png"
```

**With Background URL:**
```bash
curl -X POST "http://localhost:8000/remove-background?mode=fg-image&response_type=json" \
  -F "file=@input.png" -F "background_url=https://example.com/bg.png"
```

**Get PNG File Directly:**
```bash
curl -X POST "http://localhost:8000/remove-background?mode=fg-image&response_type=file" \
  -F "file=@input.png" --output result.png
```

#### Example JSON Response
```json
{
  "status": "success",
  "bounding_box": [x1, y1, x2, y2],
  "image_base64": "...",
  "image_size": {"width": 512, "height": 512}
}
```

#### Example File Response
- PNG image is returned directly.
- Bounding box and image size are in headers:
  - `X-Bounding-Box`: [x1, y1, x2, y2]
  - `X-Image-Width`: width
  - `X-Image-Height`: height

## Running Locally

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the server:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```
3. Visit [http://localhost:8000/docs](http://localhost:8000/docs) for Swagger UI.

## Running with Docker

1. Build the image:
   ```bash
   docker build -t background-remover-api .
   ```
2. Run the container:
   ```bash
   docker run -p 8000:8000 background-remover-api
   ```
3. Access the API at [http://localhost:8000](http://localhost:8000)

## Hosting Options

### Railway
1. Connect your GitHub repository to Railway
2. Railway will automatically detect the Python project and install dependencies
3. Set the start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### Render
1. Connect your GitHub repository to Render
2. Create a new Web Service
3. Set the build command: `pip install -r requirements.txt`
4. Set the start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### Heroku
1. Connect your GitHub repository to Heroku
2. Heroku will automatically detect the Python project
3. The `requirements.txt` file will be used to install dependencies

### DigitalOcean App Platform
1. Connect your GitHub repository to DigitalOcean App Platform
2. Select Python as the runtime
3. Set the run command: `uvicorn main:app --host 0.0.0.0 --port $PORT` 