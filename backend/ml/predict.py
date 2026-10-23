
from pathlib import Path
from datetime import datetime

import joblib
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = (
    BASE_DIR / "models" / "crowd_predictor.joblib"
)

# Load the trained Random Forest pipeline
model_data = joblib.load(MODEL_PATH)

model = model_data["model"]
features = model_data["features"]


def create_features(location_id, prediction_time):
    """
    Prepare the same features used during training.
    """

    if not isinstance(prediction_time, datetime):
        raise ValueError(
            "prediction_time must be a datetime"
        )

    hour = prediction_time.hour
    day_of_week = prediction_time.weekday()

    if not 7 <= hour <= 20:
        raise ValueError(
            "Prediction is available from 07:00 to 20:59"
        )

    return {
        "location_id": location_id,
        "hour": hour,
        "day_of_week": day_of_week,
        "is_weekend": int(day_of_week >= 5),
        "is_lunch_hour": int(12 <= hour <= 14),
        "is_class_transition": int(
            hour in [9, 11, 13, 15, 17]
        ),
    }


def predict_crowd(location_id, prediction_time):
    """
    Predict one location's crowd level.
    """

    input_data = pd.DataFrame([
        create_features(location_id, prediction_time)
    ])[features]

    prediction = model.predict(input_data)[0]

    probabilities = model.predict_proba(input_data)[0]
    classes = model.classes_

    return {
        "location_id": location_id,
        "prediction_time": prediction_time.isoformat(),
        "predicted_crowd": str(prediction),
        "confidence": round(
            float(max(probabilities) * 100), 2
        ),
        "probabilities": {
            str(label): round(float(prob), 4)
            for label, prob in zip(classes, probabilities)
        },
        "data_source": "synthetic_training_data",
    }


def predict_all_locations(locations, prediction_time):
    """
    Predict crowd levels for all campus locations.

    Returns a dictionary:
    {
        "gate": "low",
        "library": "medium",
        ...
    }
    """

    records = [
        create_features(
            location["id"],
            prediction_time
        )
        for location in locations
    ]

    if not records:
        return {}

    input_data = pd.DataFrame(records)[features]

    predictions = model.predict(input_data)

    return {
        location["id"]: str(prediction)
        for location, prediction in zip(
            locations, predictions
        )
    }
