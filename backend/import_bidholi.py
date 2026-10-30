import json
import math
import os
import re
from pathlib import Path

import psycopg
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent

JSON_FILE = (
    BASE_DIR.parent
    / "frontend"
    / "src"
    / "data"
    / "bidholi_locations.json"
)

load_dotenv(BASE_DIR / ".env")


# ------------------------------------------------------------
# CONFIRMED CAMPUS CONNECTIONS
# ------------------------------------------------------------
# Each tuple:
# (start, end, path_type, distance_factor, verified)
#
# verified=True means the connection was described by
# the student. It does NOT mean its distance was surveyed.
#
# All distances are estimates, not real measurements.
# ------------------------------------------------------------

CONNECTIONS = [
    ("Hubble", "1st Block", "walking", 1.20, True),
    ("1st Block", "2nd Block", "walking", 1.20, True),
    ("2nd Block", "3rd Block", "walking", 1.15, True),

    ("1st Block", "4th Block", "walking", 1.20, True),
    ("4th Block", "5th Block", "walking", 1.15, True),

    ("Cafe", "2nd Block", "walking", 1.20, True),
    ("Cafe", "4th Block", "walking", 1.20, True),

    ("Cafe", "Cafe Frisco", "garden", 1.05, True),

    # Approximate representation of the path-end junctions.
    # These two require further verification.
    ("Cafe Frisco", "3rd Block", "walking", 1.20, False),
    ("Cafe Frisco", "5th Block", "walking", 1.20, False),

    ("3rd Block", "Gandhi Chowk", "walking", 1.20, True),
    ("Gandhi Chowk", "6th Block", "walking", 1.20, True),

    # The staircase is confirmed, but exact crossing
    # junctions and geometry still need mapping.
    ("3rd Block", "6th Block", "stairs", 1.15, True),

    ("6th Block", "7th Block", "walking", 1.15, True),

    ("Gandhi Chowk", "9th Block", "walking", 1.20, True),
    ("Gandhi Chowk", "Boys Hostel", "walking", 1.20, True),

    ("9th Block", "10th Block", "walking", 1.15, True),
    ("10th Block", "11th Block", "walking", 1.15, True),

    # Both are reached through a road junction.
    # The simplified geometry requires refinement.
    ("6th Block", "Library", "walking", 1.30, True),
    ("6th Block", "IT Block", "walking", 1.30, True),

    ("Library", "IT Block", "road_crossing", 1.10, True),
]


# ------------------------------------------------------------
# NORMALIZATION
# ------------------------------------------------------------

def normalize_name(value):
    name = str(value or "").strip().lower()

    name = name.replace("café", "cafe")

    name = re.sub(r"\s+", " ", name)

    # Match "Block 3" with "3rd Block"
    number_to_ordinal = {
        "1": "1st",
        "2": "2nd",
        "3": "3rd",
        "4": "4th",
        "5": "5th",
        "6": "6th",
        "7": "7th",
        "8": "8th",
        "9": "9th",
        "10": "10th",
        "11": "11th",
    }

    match = re.fullmatch(r"block\s+(\d+)", name)

    if match:
        number = match.group(1)
        ordinal = number_to_ordinal.get(number)

        if ordinal:
            return f"{ordinal} block"

    return name


# ------------------------------------------------------------
# HAVERSINE DISTANCE
# ------------------------------------------------------------

def haversine(lat1, lon1, lat2, lon2):
    radius = 6371000.0

    p1 = math.radians(lat1)
    p2 = math.radians(lat2)

    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)

    a = (
        math.sin(dp / 2) ** 2
        + math.cos(p1)
        * math.cos(p2)
        * math.sin(dl / 2) ** 2
    )

    a = min(1.0, max(0.0, a))

    return 2 * radius * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )


# ------------------------------------------------------------
# DATABASE CONNECTION
# ------------------------------------------------------------

def get_connection():
    required = ["DB_NAME", "DB_USER", "DB_PASSWORD"]

    missing = [
        key for key in required
        if not os.getenv(key)
    ]

    if missing:
        raise RuntimeError(
            "Missing database settings: "
            + ", ".join(missing)
            + ". Check backend/.env."
        )

    return psycopg.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


# ------------------------------------------------------------
# LOAD AND VALIDATE JSON
# ------------------------------------------------------------

def load_locations():
    if not JSON_FILE.exists():
        raise FileNotFoundError(
            f"Location JSON not found: {JSON_FILE}"
        )

    with open(JSON_FILE, "r", encoding="utf-8") as file:
        locations = json.load(file)

    if not isinstance(locations, list):
        raise ValueError("Location JSON must be an array.")

    if len(locations) != 30:
        raise ValueError(
            f"Expected 30 locations, found {len(locations)}."
        )

    ids = set()
    names = set()
    cleaned = []

    for location in locations:
        location_id = str(location["id"])
        name = str(location["name"]).strip()

        latitude = float(location["latitude"])
        longitude = float(location["longitude"])

        if not (-90 <= latitude <= 90):
            raise ValueError(f"Invalid latitude: {name}")

        if not (-180 <= longitude <= 180):
            raise ValueError(f"Invalid longitude: {name}")

        normalized = normalize_name(name)

        if location_id in ids:
            raise ValueError(
                f"Duplicate location ID: {location_id}"
            )

        if normalized in names:
            raise ValueError(
                f"Duplicate location name: {name}"
            )

        ids.add(location_id)
        names.add(normalized)

        cleaned.append({
            "id": location_id,
            "name": name,
            "normalized": normalized,
            "latitude": latitude,
            "longitude": longitude,
            "category": location.get(
                "category", "landmark"
            ),
            "image_url": location.get("image_url"),
            "verified_entrance": bool(
                location.get("verified_entrance", False)
            ),
        })

    return cleaned


# ------------------------------------------------------------
# PREPARE EDGES
# ------------------------------------------------------------

def prepare_edges(locations):
    by_name = {
        item["normalized"]: item
        for item in locations
    }

    edges = []
    missing = []
    seen = set()

    for (
        start_name,
        end_name,
        path_type,
        factor,
        verified,
    ) in CONNECTIONS:

        start = by_name.get(normalize_name(start_name))
        end = by_name.get(normalize_name(end_name))

        if start is None or end is None:
            missing.append((start_name, end_name))
            continue

        if start["id"] == end["id"]:
            raise ValueError("Self-connection detected.")

        pair = tuple(sorted([start["id"], end["id"]]))

        if pair in seen:
            raise ValueError(
                f"Duplicate connection: {pair}"
            )

        seen.add(pair)

        direct_distance = haversine(
            start["latitude"],
            start["longitude"],
            end["latitude"],
            end["longitude"],
        )

        estimated_distance = max(
            1,
            math.ceil(direct_distance * factor)
        )

        edges.append({
            "from_id": start["id"],
            "to_id": end["id"],
            "distance": estimated_distance,
            "direct_distance": round(direct_distance, 2),
            "path_type": path_type,
            "factor": factor,
            "verified": verified,
        })

    if missing:
        print("\nWARNING: Unmatched connections:")
        for start, end in missing:
            print(f"  {start} -> {end}")

        raise ValueError(
            "Some connections could not be matched. "
            "Review the location names before importing."
        )

    return edges


# ------------------------------------------------------------
# CREATE SEPARATE BIDHOLI TABLES
# ------------------------------------------------------------

def create_tables(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bidholi_locations (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            latitude DOUBLE PRECISION NOT NULL,
            longitude DOUBLE PRECISION NOT NULL,
            image_url TEXT,
            verified_entrance BOOLEAN NOT NULL DEFAULT FALSE,
            campus_id TEXT NOT NULL DEFAULT 'bidholi'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bidholi_edges (
            id BIGINT GENERATED BY DEFAULT AS IDENTITY
                PRIMARY KEY,
            from_id TEXT NOT NULL
                REFERENCES bidholi_locations(id),
            to_id TEXT NOT NULL
                REFERENCES bidholi_locations(id),
            distance DOUBLE PRECISION NOT NULL
                CHECK (distance > 0),
            direct_distance DOUBLE PRECISION NOT NULL,
            path_factor DOUBLE PRECISION NOT NULL,
            path_type TEXT NOT NULL,
            distance_type TEXT NOT NULL DEFAULT 'estimated',
            verified_connection BOOLEAN NOT NULL DEFAULT FALSE,
            bidirectional BOOLEAN NOT NULL DEFAULT TRUE,
            UNIQUE (from_id, to_id)
        )
    """)


# ------------------------------------------------------------
# IMPORT DATA
# ------------------------------------------------------------

def import_data():
    print("\nCampusFlow - UPES Bidholi Import")
    print("-----------------------------------")

    locations = load_locations()
    edges = prepare_edges(locations)

    print(f"Validated locations: {len(locations)}")
    print(f"Prepared estimated edges: {len(edges)}")

    with get_connection() as connection:
        with connection.cursor() as cursor:

            create_tables(cursor)

            # Prevent accidental modification of a previous
            # import with different location IDs or schema.
            cursor.execute(
                "SELECT COUNT(*) FROM bidholi_locations"
            )

            existing = cursor.fetchone()[0]

            if existing > 0:
                raise RuntimeError(
                    "Bidholi tables already contain data. "
                    "Import stopped to protect existing records."
                )

            for location in locations:
                cursor.execute("""
                    INSERT INTO bidholi_locations (
                        id, name, category, latitude,
                        longitude, image_url,
                        verified_entrance, campus_id
                    )
                    VALUES (
                        %s, %s, %s, %s,
                        %s, %s, %s, 'bidholi'
                    )
                """, (
                    location["id"],
                    location["name"],
                    location["category"],
                    location["latitude"],
                    location["longitude"],
                    location["image_url"],
                    location["verified_entrance"],
                ))

            for edge in edges:
                cursor.execute("""
                    INSERT INTO bidholi_edges (
                        from_id, to_id, distance,
                        direct_distance, path_factor,
                        path_type, distance_type,
                        verified_connection,
                        bidirectional
                    )
                    VALUES (
                        %s, %s, %s, %s, %s,
                        %s, 'estimated', %s, TRUE
                    )
                """, (
                    edge["from_id"],
                    edge["to_id"],
                    edge["distance"],
                    edge["direct_distance"],
                    edge["factor"],
                    edge["path_type"],
                    edge["verified"],
                ))

            cursor.execute(
                "SELECT COUNT(*) FROM bidholi_locations"
            )
            location_count = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM bidholi_edges"
            )
            edge_count = cursor.fetchone()[0]

    print("\nImport completed successfully!")
    print(f"Total Bidholi locations: {location_count}")
    print(f"Total Bidholi edges: {edge_count}")
    print("Distance source: GPS-based estimates")
    print("Existing demo campus tables: unchanged")


if __name__ == "__main__":
    try:
        import_data()
    except Exception as error:
        print(f"\nImport failed: {error}")
        raise SystemExit(1)
