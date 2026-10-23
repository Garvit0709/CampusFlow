
from pathlib import Path

import joblib
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "campus_crowd_history.csv"
MODEL_DIR = BASE_DIR / "models"
MODEL_FILE = MODEL_DIR / "crowd_predictor.joblib"

FEATURES = [
    "location_id",
    "hour",
    "day_of_week",
    "is_weekend",
    "is_lunch_hour",
    "is_class_transition",
]

TARGET = "crowd_level"


def train_model():
    df = pd.read_csv(
        DATA_FILE,
        parse_dates=["timestamp"]
    )

    df = df.sort_values("timestamp").reset_index(drop=True)

    # Chronological split: first 80% of dates for training
    # and last 20% of dates for testing.
    unique_dates = sorted(df["timestamp"].dt.date.unique())
    split_index = int(len(unique_dates) * 0.8)

    train_dates = set(unique_dates[:split_index])
    test_dates = set(unique_dates[split_index:])

    train_df = df[
        df["timestamp"].dt.date.isin(train_dates)
    ].copy()

    test_df = df[
        df["timestamp"].dt.date.isin(test_dates)
    ].copy()

    X_train = train_df[FEATURES]
    y_train = train_df[TARGET]

    X_test = test_df[FEATURES]
    y_test = test_df[TARGET]

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "location",
                OneHotEncoder(handle_unknown="ignore"),
                ["location_id"],
            ),
            (
                "numeric",
                "passthrough",
                [
                    "hour",
                    "day_of_week",
                    "is_weekend",
                    "is_lunch_hour",
                    "is_class_transition",
                ],
            ),
        ]
    )

    model = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=200,
                    max_depth=12,
                    min_samples_leaf=3,
                    random_state=42,
                    n_jobs=-1,
                ),
            ),
        ]
    )

    print("Training CampusFlow Crowd Prediction Model...")

    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    accuracy = accuracy_score(y_test, predictions)

    # Baseline: predict the most frequent training label
    baseline_label = y_train.mode().iloc[0]
    baseline_predictions = [baseline_label] * len(y_test)
    baseline_accuracy = accuracy_score(
        y_test, baseline_predictions
    )

    print("\nDataset Information")
    print("-" * 45)
    print("Training records:", len(train_df))
    print("Testing records:", len(test_df))
    print("Training date range:",
          train_df["timestamp"].min(),
          "to",
          train_df["timestamp"].max())
    print("Testing date range:",
          test_df["timestamp"].min(),
          "to",
          test_df["timestamp"].max())

    print("\nModel Evaluation")
    print("-" * 45)
    print(f"Baseline Accuracy: {baseline_accuracy:.2%}")
    print(f"Random Forest Accuracy: {accuracy:.2%}")

    print("\nClassification Report:")
    print(
        classification_report(
            y_test,
            predictions,
            labels=["low", "medium", "high"],
            zero_division=0,
        )
    )

    print("\nConfusion Matrix:")
    print(
        confusion_matrix(
            y_test,
            predictions,
            labels=["low", "medium", "high"],
        )
    )

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    joblib.dump(
        {
            "model": model,
            "features": FEATURES,
            "training_source": "synthetic_campus_data",
        },
        MODEL_FILE,
    )

    print("\nModel saved successfully!")
    print("Location:", MODEL_FILE)


if __name__ == "__main__":
    train_model()
