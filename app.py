from fastapi import FastAPI, File, UploadFile
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import load_img, img_to_array
import numpy as np
import io

# ---------------- APP INIT ----------------
app = FastAPI(title="Grape Disease Detection API")

# ---------------- LOAD MODEL ----------------
model = load_model("grape_disease_model.h5")

# ---------------- CLASS NAMES ----------------
CLASS_NAMES = [
    "Grape Black Rot",
    "Grape Esca (Black Measles)",
    "Grape Healthy",
    "Grape Leaf Blight"
]

# ---------------- REMEDIES ----------------
REMEDIES = {
    "Grape Black Rot": "Apply fungicides like Mancozeb or Myclobutanil. Remove infected leaves.",
    "Grape Esca (Black Measles)": "Prune infected vines, avoid wounds, use trunk protection fungicides.",
    "Grape Healthy": "Plant is healthy. Maintain proper irrigation and regular monitoring.",
    "Grape Leaf Blight": "Use copper-based fungicides and ensure proper air circulation."
}

# ---------------- ROUTES ----------------
@app.get("/")
def home():
    return {
        "message": "🍇 Grape Disease Detection API is running"
    }

@app.post("/predict")
async def predict_disease(file: UploadFile = File(...)):
    # Read image
    image_bytes = await file.read()

    # Preprocess image
    img = load_img(io.BytesIO(image_bytes), target_size=(224, 224))
    img = img_to_array(img) / 255.0
    img = np.expand_dims(img, axis=0)

    # Predict
    predictions = model.predict(img)
    class_index = int(np.argmax(predictions))
    confidence = float(np.max(predictions))

    disease = CLASS_NAMES[class_index]

    return {
        "disease": disease,
        "confidence": round(confidence * 100, 2),
        "solution": REMEDIES[disease]
    }
