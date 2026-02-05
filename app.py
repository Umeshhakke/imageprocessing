from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import load_img, img_to_array
import numpy as np
import io
import h5py
import json
import os
import uvicorn

# ---------------- APP INIT ----------------
app = FastAPI(title="🍇 Grape Disease Detection API")

# ---------------- HELPER FUNCTION TO FIX MODEL ----------------
def load_h5_model_fixed(path: str):
    """
    Fix H5 model config to remove unsupported 'groups' argument
    in DepthwiseConv2D layers, then loads the model.
    """
    with h5py.File(path, "r+") as f:
        if "model_config" in f.attrs:
            config_str = f.attrs["model_config"].decode("utf-8")
            config_dict = json.loads(config_str)

            # Recursively remove 'groups' keys
            def remove_groups(d):
                if isinstance(d, dict):
                    d.pop("groups", None)
                    for v in d.values():
                        remove_groups(v)
                elif isinstance(d, list):
                    for item in d:
                        remove_groups(item)

            remove_groups(config_dict)
            # Save back the fixed config
            f.attrs["model_config"] = json.dumps(config_dict).encode("utf-8")

    # Load the fixed model
    return load_model(path)

# ---------------- LOAD MODEL ----------------
model = load_h5_model_fixed("grape_disease_model.h5")

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
@app.get("/", response_class=HTMLResponse)
def home_page():
    return """
    <html>
        <head>
            <title>Grape Disease Detection</title>
        </head>
        <body>
            <h1>🍇 Grape Disease Detection</h1>
            <p>Upload an image of a grape leaf to detect disease.</p>
            <form action="/predict_web" method="post" enctype="multipart/form-data">
                <input type="file" name="file" accept="image/*" required>
                <input type="submit" value="Predict Disease">
            </form>
        </body>
    </html>
    """

@app.post("/predict_web", response_class=HTMLResponse)
async def predict_disease_web(file: UploadFile = File(...)):
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
    solution = REMEDIES[disease]

    # Return result as HTML
    return f"""
    <html>
        <head>
            <title>Grape Disease Result</title>
        </head>
        <body>
            <h1>🍇 Prediction Result</h1>
            <p><strong>Disease:</strong> {disease}</p>
            <p><strong>Confidence:</strong> {round(confidence*100, 2)}%</p>
            <p><strong>Solution:</strong> {solution}</p>
            <a href="/">🔙 Back to Upload</a>
        </body>
    </html>
    """

@app.post("/predict")
async def predict_disease_api(file: UploadFile = File(...)):
    """
    Original API route for programmatic access
    """
    image_bytes = await file.read()
    img = load_img(io.BytesIO(image_bytes), target_size=(224, 224))
    img = img_to_array(img) / 255.0
    img = np.expand_dims(img, axis=0)

    predictions = model.predict(img)
    class_index = int(np.argmax(predictions))
    confidence = float(np.max(predictions))

    disease = CLASS_NAMES[class_index]

    return {
        "disease": disease,
        "confidence": round(confidence * 100, 2),
        "solution": REMEDIES[disease]
    }

# ---------------- RUN SERVER ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))  # Use Render port or default 8000
    uvicorn.run("app:app", host="0.0.0.0", port=port)
