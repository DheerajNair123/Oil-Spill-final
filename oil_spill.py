from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image
import numpy as np
from io import BytesIO
import tensorflow as tf
import os
from typing import Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app instance
app = FastAPI(
    title="Oil Spill Detection API",
    description="Detects oil spills in satellite images using deep learning",
    version="1.0"
)

# Get model path from environment variable or use default
model_path = os.getenv('MODEL_PATH', './model.h5')

# Load the model once at startup
model = None

@app.on_event("startup")
async def load_model():
    global model
    try:
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found at {model_path}")
        model = tf.keras.models.load_model(model_path)
        logger.info(f"Model loaded successfully from {model_path}")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise

def preprocess_image(contents: bytes, target_size: tuple = (224, 224)) -> np.ndarray:
    """
    Preprocess image for model prediction.

    Args:
        contents: Raw image bytes
        target_size: Target dimensions (height, width)

    Returns:
        Preprocessed image array with batch dimension

    Raises:
        ValueError: If image format is invalid
    """
    try:
        # Open the image with PIL
        img = Image.open(BytesIO(contents))

        # Convert to RGB if necessary (handles RGBA, grayscale, etc.)
        if img.mode != 'RGB':
            img = img.convert('RGB')

        # Resize the image to target size
        img = img.resize(target_size)

        # Convert to numpy array and normalize
        img_array = np.array(img, dtype=np.float32) / 255.0

        # Add batch dimension
        img_array = np.expand_dims(img_array, axis=0)

        return img_array
    except Image.UnidentifiedImageError:
        raise ValueError("Uploaded file is not a valid image")
    except Exception as e:
        raise ValueError(f"Error processing image: {str(e)}")

@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint"""
    return {"status": "Oil Spill Detection API is running"}

@app.post("/predict/", tags=["Prediction"])
async def predict(file: UploadFile = File(...)) -> JSONResponse:
    """
    Predict whether an image contains an oil spill.

    Args:
        file: Image file to analyze

    Returns:
        JSON with prediction label and confidence score
    """
    # Validate file type
    if file.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only JPEG and PNG are supported"
        )

    # Validate file size (max 5MB)
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="File size exceeds 5MB limit"
        )

    try:
        if model is None:
            raise RuntimeError("Model not loaded")

        # Preprocess the image
        image = preprocess_image(contents)

        # Perform prediction
        prediction = model.predict(image, verbose=0)[0][0]

        # Determine the label based on prediction
        label = "Oil Spill" if prediction >= 0.5 else "Not Oil Spill"
        confidence = float(prediction)

        return JSONResponse({
            "label": label,
            "confidence": confidence,
            "threshold": 0.5
        })

    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
