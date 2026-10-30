import csv
import math
import os
from collections import defaultdict, deque
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

REPORT_FILE = BASE_DIR / "bidholi_geometry_report.csv"

# Review thresholds, not official campus measurements.
LONG_SEGMENT_METERS = 200
HIGH_FACTOR = 1.5
LOW_FACTOR = 0.95


def connect():
    return psycopg.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "campusflow_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
        row_factory=dict_row,
    )


def haversine(lat1, lon1, lat2, lon2):
    radius = 6371000

    p1 = math.radians(lat1)
    p2 = math.radians(lat2)

    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)

    a = (
        math.sin(dp / 2) ** 2
        + math.cos(p1) * math.cos(p2)
        * math.sin(dl / 2) ** 2
    )

    a = min(1.0, max(0.0, a))

    return 2 * radius * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )


def load_data():
    with connect() as conn:
        buildings = conn.execute("""
            SELECT id, name, latitude, longitude
            FROM bidholi_locations
        """).fetchall()

        junctions = conn.execute("""
            SELECT
                id, name, latitude, longitude,
                verified_on_ground
            FROM bidholi_junctions
        """).fetchall()

        edges = conn.execute("""
            SELECT
                id, from_id, to_id, distance,
                direct_distance, path_factor,
                path_type, bidirectional,
                verified_connection, geometry_verified
            FROM bidholi_pedestrian_edges
        """).fetchall()

    return buildings, junctions, edges


def check_connectivity(nodes, edges, avoid_stairs=False):
    graph = defaultdict(list)

    for edge in edges:
        if avoid_stairs and edge["path_type"] == "stairs":
            continue

        a = edge["from_id"]
        b = edge["to_id"]

        if a not in nodes or b not in nodes:
            continue

        graph[a].append(b)

        if edge["bidirectional"]:
            graph[b].append(a)

    start = "bidholi-19"

    if start not in nodes:
        return set()

    visited = {start}
    queue = deque([start])

    while queue:
        current = queue.popleft()

        for neighbor in graph[current]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)

    return visited


def validate():
    buildings, junctions, edges = load_data()

    nodes = {}

    for node in buildings + junctions:
        if node["id"] in nodes:
            raise ValueError(
                f"Duplicate node ID: {node['id']}"
            )
        nodes[node["id"]] = node

    report = []
    issue_count = 0
    seen_pairs = set()

    for edge in edges:
        issues = []

        a = nodes.get(edge["from_id"])
        b = nodes.get(edge["to_id"])

        direct = None
        distance = edge["distance"]

        if not a or not b:
            issues.append("Unknown endpoint")
        else:
            coords = [
                a["latitude"], a["longitude"],
                b["latitude"], b["longitude"]
            ]

            if not all(
                isinstance(v, (int, float))
                and math.isfinite(v)
                for v in coords
            ):
                issues.append("Invalid GPS coordinates")
            else:
                direct = haversine(
                    a["latitude"],
                    a["longitude"],
                    b["latitude"],
                    b["longitude"]
                )

                if direct > LONG_SEGMENT_METERS:
                    issues.append("Long GPS segment")

        if distance is None or not math.isfinite(
            float(distance)
        ) or float(distance) <= 0:
            issues.append("Invalid estimated distance")
        elif direct is not None:
            if direct > 1 and distance < direct * LOW_FACTOR:
                issues.append(
                    "Estimated distance below GPS distance"
                )

        factor = edge["path_factor"]

        if factor is None or not math.isfinite(
            float(factor)
        ) or float(factor) <= 0:
            issues.append("Invalid path factor")
        elif factor > HIGH_FACTOR:
            issues.append("High path adjustment factor")

        pair = tuple(sorted((
            edge["from_id"], edge["to_id"]
        )))

        if pair in seen_pairs:
            issues.append("Duplicate undirected connection")

        seen_pairs.add(pair)

        if edge["from_id"] == edge["to_id"]:
            issues.append("Self connection")

        if not edge["geometry_verified"]:
            issues.append("Geometry not ground verified")

        if not edge["verified_connection"]:
            issues.append("Connection not confirmed")

        if issues:
            issue_count += 1

        report.append({
            "edge_id": edge["id"],
            "from_id": edge["from_id"],
            "to_id": edge["to_id"],
            "path_type": edge["path_type"],
            "estimated_m": distance,
            "gps_straight_m": (
                round(direct, 2)
                if direct is not None else ""
            ),
            "path_factor": factor,
            "issues": "; ".join(issues) or "None",
        })

    reachable = check_connectivity(
        nodes, edges, avoid_stairs=False
    )

    stair_free_reachable = check_connectivity(
        nodes, edges, avoid_stairs=True
    )

    unreachable = sorted(set(nodes) - reachable)

    stair_free_unreachable = sorted(
        set(nodes) - stair_free_reachable
    )

    with REPORT_FILE.open(
        "w", newline="", encoding="utf-8-sig"
    ) as file:
        writer = csv.DictWriter(
            file, fieldnames=list(report[0].keys())
        )
        writer.writeheader()
        writer.writerows(report)

    print("\nCAMPUSFLOW GEOMETRY VALIDATION")
    print("=" * 40)

    print("Buildings:", len(buildings))
    print("Junctions:", len(junctions))
    print("Total nodes:", len(nodes))
    print("Pedestrian edges:", len(edges))
    print("Edges with review flags:", issue_count)

    print("\nNETWORK CONNECTIVITY")
    print("Reachable:", len(reachable))
    print("Unreachable:", len(unreachable))
    print(
        "Reachable without stairs:",
        len(stair_free_reachable)
    )

    if unreachable:
        print("Unreachable nodes:", unreachable)

    if stair_free_unreachable:
        print(
            "Stair-free unreachable nodes:",
            stair_free_unreachable
        )

    print("\nJUNCTION VERIFICATION")

    unverified = [
        j["id"] for j in junctions
        if not j["verified_on_ground"]
    ]

    print("Unverified junctions:", unverified)

    print("\nCSV report saved:")
    print(REPORT_FILE)
    print("\nDatabase records were not modified.")


if __name__ == "__main__":
    try:
        validate()
    except Exception as error:
        print("Validation failed:", error)
        raise SystemExit(1)
