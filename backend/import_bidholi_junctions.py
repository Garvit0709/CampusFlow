
# CampusFlow Phase 9.7.3
# Safe import of UPES Bidholi pedestrian junctions

import json
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

JSON_FILE = BASE_DIR / "bidholi_junctions.json"
EXPECTED_IDS = {f"J{i}" for i in range(1, 11)}


def connect():
    return psycopg.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "campusflow_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
    )


def load_and_validate():
    if not JSON_FILE.exists():
        raise FileNotFoundError(
            f"Missing file: {JSON_FILE}"
        )

    with JSON_FILE.open(encoding="utf-8") as file:
        data = json.load(file)

    if data.get("campus") != "UPES Bidholi":
        raise ValueError("Incorrect campus.")

    if data.get("schema_version") != 1:
        raise ValueError("Unsupported schema version.")

    if data.get("coordinate_system") != "WGS84":
        raise ValueError("Expected WGS84 coordinates.")

    junctions = data.get("junctions")

    if not isinstance(junctions, list):
        raise ValueError("Invalid junction list.")

    ids = [item.get("id") for item in junctions]

    if len(ids) != 10 or set(ids) != EXPECTED_IDS:
        raise ValueError(
            "Exactly J1 through J10 must be present."
        )

    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate junction IDs.")

    for item in junctions:
        lat = item.get("latitude")
        lon = item.get("longitude")

        if (
            isinstance(lat, bool)
            or isinstance(lon, bool)
            or not isinstance(lat, (int, float))
            or not isinstance(lon, (int, float))
            or not 30.0 <= lat <= 31.0
            or not 77.0 <= lon <= 79.0
        ):
            raise ValueError(
                f"Invalid coordinates: {item['id']}"
            )

        if not isinstance(item.get("name"), str):
            raise ValueError("Invalid junction name.")

        if item.get("verified_on_ground") is not False:
            raise ValueError(
                "Expected unverified map-placed junctions."
            )

    return junctions


def import_junctions():
    junctions = load_and_validate()

    print("Validated junctions:", len(junctions))

    with connect() as conn:
        with conn.cursor() as cursor:

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS
                bidholi_junctions (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    latitude DOUBLE PRECISION NOT NULL,
                    longitude DOUBLE PRECISION NOT NULL,
                    position_source TEXT NOT NULL,
                    verified_on_ground BOOLEAN
                        NOT NULL DEFAULT FALSE,
                    campus_id TEXT NOT NULL
                        DEFAULT 'bidholi'
                )
            """)

            # Protect previous data. No automatic
            # overwriting or deletion.
            cursor.execute("""
                SELECT COUNT(*)
                FROM bidholi_junctions
            """)

            existing_count = cursor.fetchone()[0]

            if existing_count != 0:
                raise RuntimeError(
                    "Junction table already contains data. "
                    "Import stopped to prevent overwriting."
                )

            for item in junctions:
                cursor.execute("""
                    INSERT INTO bidholi_junctions (
                        id,
                        name,
                        latitude,
                        longitude,
                        position_source,
                        verified_on_ground,
                        campus_id
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, 'bidholi'
                    )
                """, (
                    item["id"],
                    item["name"],
                    item["latitude"],
                    item["longitude"],
                    item.get(
                        "position_source",
                        "manual_map_click"
                    ),
                    False,
                ))

            cursor.execute("""
                SELECT COUNT(*)
                FROM bidholi_junctions
            """)

            count = cursor.fetchone()[0]

    print("Import successful!")
    print("Total junctions:", count)
    print("Existing building and edge tables unchanged.")
    print("Ground verification: pending")


if __name__ == "__main__":
    try:
        import_junctions()
    except Exception as error:
        print("Import failed:", error)
        raise SystemExit(1)
