import math
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

BASE = Path(__file__).resolve().parent
load_dotenv(BASE / ".env")

WALKING = [
    # Main entrance
    ("bidholi-19", "bidholi-18"),  # Gate - Hubble
    ("bidholi-19", "bidholi-16"),  # Gate - Enrollment
    ("bidholi-19", "bidholi-14"),  # Gate - MAC
    ("bidholi-19", "bidholi-20"),  # Gate - Food Court
    ("bidholi-16", "bidholi-14"),  # Enrollment - MAC
    ("bidholi-18", "bidholi-17"),  # Hubble - 1st

    # Academic blocks
    ("bidholi-17", "bidholi-21"), # 1st - 2nd
    ("bidholi-21", "bidholi-22"), # 2nd - 3rd
    ("bidholi-17", "bidholi-24"), # 1st - 4th
    ("bidholi-24", "bidholi-23"), # 4th - 5th

    # Midway junctions
    ("bidholi-21", "J1"),
    ("bidholi-22", "J1"),
    ("J1", "J3"),
    ("J3", "J2"),
    ("J2", "bidholi-24"),
    ("J2", "bidholi-23"),
    ("J2", "bidholi-20"),

    # Cafe and Frisco
    ("J3", "bidholi-25"),
    ("J3", "bidholi-26"),

    # Gandhi Chowk
    ("bidholi-22", "bidholi-6"),
    ("bidholi-23", "J5"),
    ("J5", "bidholi-6"),

    # Side road toward MAC
    ("bidholi-21", "J7"),
    ("bidholi-22", "J7"),
    ("J7", "bidholi-14"),

    # 6th, 7th, Library and IT
    ("bidholi-6", "bidholi-8"),
    ("bidholi-8", "bidholi-7"),
    ("bidholi-8", "bidholi-9"),
    ("bidholi-8", "bidholi-29"),
    ("bidholi-9", "bidholi-29"),
    ("bidholi-14", "J6"),
    ("J6", "bidholi-9"),
    ("J6", "bidholi-29"),

    # MAC and Gym share a building
    ("bidholi-14", "bidholi-15"),

    # MAC to Food Court 2
    ("bidholi-14", "J9"),
    ("J9", "bidholi-13"),

    # Gandhi Chowk to lower blocks
    ("bidholi-6", "bidholi-1"),
    ("bidholi-1", "bidholi-30"),
    ("bidholi-30", "bidholi-2"),

    # Laboratory and Boys Hostel area
    ("bidholi-2", "bidholi-4"),
    ("bidholi-4", "bidholi-5"),
    ("bidholi-4", "bidholi-3"),
    ("bidholi-5", "bidholi-3"),
    ("bidholi-5", "bidholi-6"),

    # Museum-side road
    ("bidholi-6", "J8"),
    ("J8", "bidholi-10"),
    ("J8", "bidholi-13"),
    ("J8", "bidholi-28"),
    ("J8", "bidholi-27"),
    ("J8", "bidholi-11"),

    # Museum and recreation area
    ("bidholi-10", "bidholi-11"),
    ("bidholi-10", "bidholi-28"),
    ("bidholi-11", "bidholi-12"),
    ("bidholi-11", "bidholi-27"),
    ("bidholi-12", "bidholi-28"),

    # Management and Girls Hostel
    ("bidholi-28", "J10"),
    ("J10", "bidholi-27"),
]

STAIRS = [
    # Staircase crossing between 3rd and 6th
    ("bidholi-22", "J4"),
    ("J4", "bidholi-8"),
]


def connect():
    return psycopg.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "campusflow_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
    )


def haversine(a, b):
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    value = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    value = min(1.0, max(0.0, value))

    return (
        6371000
        * 2
        * math.asin(math.sqrt(value))
    )


def load_nodes(cursor):
    cursor.execute("""
        SELECT id, name, latitude, longitude
        FROM bidholi_locations
    """)

    buildings = cursor.fetchall()

    cursor.execute("""
        SELECT id, name, latitude, longitude
        FROM bidholi_junctions
    """)

    junctions = cursor.fetchall()

    nodes = {}

    for node_id, name, lat, lon in (
        buildings + junctions
    ):
        if node_id in nodes:
            raise ValueError(
                f"Duplicate node ID: {node_id}"
            )

        nodes[node_id] = {
            "name": name,
            "coordinates": (float(lat), float(lon)),
        }

    if len(buildings) != 30:
        raise ValueError("Expected 30 buildings.")

    if len(junctions) != 10:
        raise ValueError("Expected 10 junctions.")

    return nodes


def prepare_edges(nodes):
    prepared = []
    seen = set()

    for path_type, connections, factor in [
        ("walking", WALKING, 1.20),
        ("stairs", STAIRS, 1.30),
    ]:
        for start, end in connections:
            if start not in nodes or end not in nodes:
                raise ValueError(
                    f"Unknown node: {start} -> {end}"
                )

            if start == end:
                raise ValueError("Self-edge detected.")

            key = tuple(sorted((start, end)))

            if key in seen:
                raise ValueError(
                    f"Duplicate edge: {key}"
                )

            seen.add(key)

            direct = haversine(
                nodes[start]["coordinates"],
                nodes[end]["coordinates"],
            )

            estimated = max(
                1.0,
                float(math.ceil(direct * factor))
            )

            prepared.append((
                start,
                end,
                estimated,
                round(direct, 2),
                factor,
                path_type,
            ))

    return prepared


def create_table(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS
        bidholi_pedestrian_edges (
            id BIGINT GENERATED ALWAYS AS IDENTITY
                PRIMARY KEY,
            from_id TEXT NOT NULL,
            to_id TEXT NOT NULL,
            distance DOUBLE PRECISION NOT NULL
                CHECK (distance > 0),
            direct_distance DOUBLE PRECISION NOT NULL,
            path_factor DOUBLE PRECISION NOT NULL,
            path_type TEXT NOT NULL,
            distance_type TEXT NOT NULL
                DEFAULT 'estimated',
            bidirectional BOOLEAN NOT NULL
                DEFAULT TRUE,
            verified_connection BOOLEAN NOT NULL
                DEFAULT TRUE,
            geometry_verified BOOLEAN NOT NULL
                DEFAULT FALSE,
            UNIQUE (from_id, to_id)
        )
    """)


def build():
    with connect() as conn:
        with conn.cursor() as cursor:
            nodes = load_nodes(cursor)
            edges = prepare_edges(nodes)

            print("Buildings: 30")
            print("Junctions: 10")
            print("Prepared edges:", len(edges))

            create_table(cursor)

            cursor.execute("""
                SELECT COUNT(*)
                FROM bidholi_pedestrian_edges
            """)

            existing = cursor.fetchone()[0]

            if existing:
                raise RuntimeError(
                    "Pedestrian edge table already has "
                    "data. Import stopped to protect it."
                )

            for edge in edges:
                cursor.execute("""
                    INSERT INTO bidholi_pedestrian_edges (
                        from_id,
                        to_id,
                        distance,
                        direct_distance,
                        path_factor,
                        path_type,
                        distance_type,
                        bidirectional,
                        verified_connection,
                        geometry_verified
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s,
                        'estimated', TRUE, TRUE, FALSE
                    )
                """, edge)

            cursor.execute("""
                SELECT COUNT(*)
                FROM bidholi_pedestrian_edges
            """)

            count = cursor.fetchone()[0]

    print("Pedestrian graph created successfully!")
    print("Total nodes:", len(nodes))
    print("Total pedestrian edges:", count)
    print("Existing routing tables: unchanged")
    print("Distances: estimated, not surveyed")


if __name__ == "__main__":
    try:
        build()
    except Exception as error:
        print("Graph build failed:", error)
        raise SystemExit(1)
