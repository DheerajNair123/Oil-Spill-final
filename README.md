# Oil Spill Detection API

A FastAPI-based web service for detecting oil spills in satellite imagery using deep learning.

## What This Code Does

The application accepts satellite images and uses a trained TensorFlow neural network to classify whether the image contains an oil spill or not. It returns a confidence score along with the classification.

**Flow:**
1. User uploads an image via HTTP POST
2. Image is validated (format, size)
3. Image is preprocessed (resized to 224×224, normalized)
4. Model makes prediction
5. API returns classification and confidence score

## Installation & Setup

### 1. Clone/Navigate to Project
```bash
cd /path/to/oil_spill/project
```

### 2. Create Virtual Environment (Recommended)
```bash
python -m venv venv
source venv/Scripts/activate  # Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Prepare Your Model
- Place your trained model file as `model.h5` in the project directory
- OR set the `MODEL_PATH` environment variable:
```bash
export MODEL_PATH=/path/to/your/model.h5  # Linux/Mac
set MODEL_PATH=C:\path\to\model.h5         # Windows
```

## Running the API

### Start the Server
```bash
uvicorn oil_spill:app --reload
```

The API will be available at: **http://localhost:8000**

### Interactive API Documentation
Visit: **http://localhost:8000/docs** (Swagger UI)
Or: **http://localhost:8000/redoc** (ReDoc)

## Testing

### Using Swagger UI (Easiest)
1. Go to http://localhost:8000/docs
2. Click on the `/predict/` endpoint
3. Click "Try it out"
4. Upload an image
5. Click "Execute"

### Using curl
```bash
curl -X POST "http://localhost:8000/predict/" \
  -F "file=@satellite_image.jpg"
```

### Using Python
```bash
python test_api.py
```

### Example Response
```json
{
  "label": "Oil Spill",
  "confidence": 0.87,
  "threshold": 0.5
}
```

## API Endpoints

### 1. Health Check
**GET** `/`
- Returns: `{"status": "Oil Spill Detection API is running"}`

### 2. Make Prediction
**POST** `/predict/`
- **Input:** Image file (JPEG/PNG, max 5MB)
- **Output:**
  ```json
  {
    "label": "Oil Spill" or "Not Oil Spill",
    "confidence": 0.0-1.0,
    "threshold": 0.5
  }
  ```
- **Error Codes:**
  - `400`: Invalid file type or format
  - `413`: File too large (>5MB)
  - `500`: Server error

## Key Improvements Made

### 1. **Error Handling**
- File type validation (JPEG/PNG only)
- File size limits (5MB max)
- Graceful error messages
- Logging of all errors

### 2. **Image Preprocessing**
- Handles different image formats (converts RGBA/grayscale to RGB)
- Robust error handling for corrupted images
- Normalized pixel values (0-1 range)

### 3. **Production Ready**
- Proper logging system
- Health check endpoint
- Model loaded at startup (not per request)
- Type hints for better code clarity
- API documentation

### 4. **Better Configuration**
- Model path configurable via environment variable
- No hardcoded paths
- Support for .env files

### 5. **Security**
- File size limits prevent DOS attacks
- File type validation prevents malicious uploads
- Verbose error messages disabled in production

## Performance Tips

1. **GPU Support**: Ensure TensorFlow can access GPU for faster predictions
   ```bash
   python -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"
   ```

2. **Batch Processing**: For multiple images, consider modifying to accept batch uploads

3. **Caching**: Add Redis caching for repeated predictions on same images

4. **Load Balancing**: Deploy multiple instances behind a load balancer for production

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Model not found | Check `MODEL_PATH` environment variable and file exists |
| Port 8000 in use | Change port: `uvicorn oil_spill:app --port 8001` |
| Image processing error | Ensure image is valid JPEG/PNG, not corrupted |
| Slow predictions | Check GPU usage; consider model optimization |
| 500 errors | Check logs for detailed error messages |

## Project Structure
```
oil_spill/
├── oil_spill.py          # Main API code
├── requirements.txt      # Dependencies
├── .env.example         # Environment template
├── test_api.py          # Test suite
├── run.sh               # Startup script
├── model.h5             # Trained model (add this)
└── README.md            # This file
```

## Environment Variables

Create a `.env` file:
```
MODEL_PATH=./model.h5
API_HOST=0.0.0.0
API_PORT=8000
```

## Production Deployment

For production, use a production ASGI server:
```bash
pip install gunicorn
gunicorn oil_spill:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## License
College Mini Project (semVII)

## Author
Dheeraj
