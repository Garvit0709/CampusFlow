
from pathlib import Path
from datetime import datetime, timedelta

import numpy as np
import pandas as pd


# -----------------------------------
# CONFIGURATION
# -----------------------------------

RANDOM_SEED = 42
DAYS = 90

START_DATE = datetime(2026, 7, 1)

START_HOUR = 7
END_HOUR = 20

OUTPUT_DIR = Path(__file__).resolve().parent / "data"
OUTPUT_FILE = OUTPUT_DIR / "campus_crowd_history.csv"

rng = np.random.default_rng(RANDOM_SEED)


# -----------------------------------
# CAMPUS LOCATIONS
# -----------------------------------

LOCATIONS = {
    "gate": {
        "name": "Main Gate",
        "base_crowd": 30,
    },
    "library": {
        "name": "Central Library",
        "base_crowd": 35,
    },
    "blockA": {
        "name": "Academic Block A",
        "base_crowd": 40,
    },
    "cafeteria": {
        "name": "Cafeteria",
        "base_crowd": 30,
    },
    "hostel": {
        "name": "Student Hostel",
        "base_crowd": 35,
    },
    "sports": {
        "name": "Sports Complex",
        "base_crowd": 20,
    },
}


# -----------------------------------
# CROWD PATTERN SIMULATION
# -----------------------------------

def calculate_crowd_score(
    location_id,
    hour,
    day_of_week,
):
    """
    Generate simulated crowd scores using
    location, time, and assumed campus patterns.

    This is synthetic data, not measured
    real-world crowd information.
    """

    base = LOCATIONS[location_id]["base_crowd"]

    is_weekend = day_of_week >= 5
    is_lunch_hour = 12 <= hour <= 14
    is_class_transition = hour in [9, 11, 13, 15, 17]

    score = base

    # -----------------------------------
    # WEEKEND EFFECT
    # -----------------------------------

    if is_weekend:
        if location_id in ["library", "blockA", "gate"]:
            score -= 20

        elif location_id in ["sports", "hostel"]:
            score += 10

    # -----------------------------------
    # LOCATION-SPECIFIC PATTERNS
    # -----------------------------------

    if location_id == "gate":
        if hour in [8, 9, 16, 17]:
            score += 35

    elif location_id == "library":
        if 10 <= hour <= 17:
            score += 20

        if hour in [12, 13]:
            score += 10

    elif location_id == "blockA":
        if 9 <= hour <= 16:
            score += 25

        if is_class_transition:
            score += 15

    elif location_id == "cafeteria":
        if is_lunch_hour:
            score += 50

        if hour in [16, 17]:
            score += 20

    elif location_id == "hostel":
        if hour in [7, 8, 18, 19, 20]:
            score += 25

    elif location_id == "sports":
        if hour in [16, 17, 18, 19]:
            score += 45

    # -----------------------------------
    # RANDOM VARIATION
    # -----------------------------------

    noise = rng.normal(loc=0, scale=8)

    score += noise

    # Keep score between 0 and 100
    score = float(np.clip(score, 0, 100))

    return round(score, 2)


# -----------------------------------
# CROWD CLASSIFICATION
# -----------------------------------

def classify_crowd(score):
    if score < 35:
        return "low"

    elif score < 65:
        return "medium"

    return "high"


# -----------------------------------
# DATASET GENERATION
# -----------------------------------

def generate_dataset():
    records = []

    for day_offset in range(DAYS):
        current_date = START_DATE + timedelta(
            days=day_offset
        )

        day_of_week = current_date.weekday()

        for hour in range(
            START_HOUR,
            END_HOUR + 1
        ):
            timestamp = current_date.replace(
                hour=hour,
                minute=0,
                second=0,
                microsecond=0,
            )

            is_weekend = int(day_of_week >= 5)

            is_lunch_hour = int(
                12 <= hour <= 14
            )

            is_class_transition = int(
                hour in [9, 11, 13, 15, 17]
            )

            for location_id, details in LOCATIONS.items():

                crowd_score = calculate_crowd_score(
                    location_id,
                    hour,
                    day_of_week,
                )

                crowd_level = classify_crowd(
                    crowd_score
                )

                records.append({
                    "timestamp": timestamp,
                    "location_id": location_id,
                    "location_name": details["name"],
                    "hour": hour,
                    "day_of_week": day_of_week,
                    "is_weekend": is_weekend,
                    "is_lunch_hour": is_lunch_hour,
                    "is_class_transition": is_class_transition,
                    "crowd_score": crowd_score,
                    "crowd_level": crowd_level,
                })

    df = pd.DataFrame(records)

    # Sort chronologically
    df = df.sort_values(
        by=["timestamp", "location_id"]
    ).reset_index(drop=True)

    # Create output directory
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # Save dataset
    df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print("\nCampusFlow Dataset Generated!")
    print("-" * 45)

    print("Total Records:", len(df))
    print("Total Locations:", df["location_id"].nunique())

    print("Start Date:", df["timestamp"].min())
    print("End Date:", df["timestamp"].max())

    print("\nCrowd Level Distribution:")
    print(df["crowd_level"].value_counts())

    print("\nMissing Values:")
    print(df.isnull().sum())

    print("\nFirst Five Records:")
    print(df.head())

    print("\nDataset saved to:")
    print(OUTPUT_FILE)


# -----------------------------------
# RUN SCRIPT
# -----------------------------------

if __name__ == "__main__":
    generate_dataset()
