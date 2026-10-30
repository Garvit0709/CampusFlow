
"""
CampusFlow Phase 9.8.6
Comprehensive UPES Bidholi pedestrian route tests.

Tests all 30 building destinations:
- Every ordered source/destination pair
- Shortest and stair-free routing
- Dijkstra result validity
- Path connectivity and edge direction
- Staircase restrictions
- GPS coordinates and estimated distances

Read-only: no database modifications.
"""

import csv
import math
import os
from collections import Counter
from datetime import datetime
from itertools import permutations
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

from bidholi_pedestrian_routing import (
    shortest_path,
)

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

REPORT_DIR = BASE_DIR / "test_reports"
REPORT_DIR.mkdir(exist_ok=True)

REPORT_PATH = (
    REPORT_DIR / "bidholi_route_test_report.csv"
)

SUMMARY_PATH = (
    REPORT_DIR / "bidholi_route_test_summary.txt"
)


def connect():
    return psycopg.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "campusflow_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
        row_factory=dict_row,
    )


def load_test_data():
    with connect() as conn:
        buildings = conn.execute("""
            SELECT id, name, latitude, longitude
            FROM bidholi_locations
            ORDER BY id
        """).fetchall()

        junctions = conn.execute("""
            SELECT id, name, latitude, longitude
            FROM bidholi_junctions
            ORDER BY id
        """).fetchall()

        edges = conn.execute("""
            SELECT
                id,
                from_id,
                to_id,
                distance,
                path_type,
                bidirectional,
                verified_connection,
                geometry_verified
            FROM bidholi_pedestrian_edges
            ORDER BY id
        """).fetchall()

    nodes = {}

    for item in buildings + junctions:
        node_id = item["id"]

        if node_id in nodes:
            raise ValueError(
                f"Duplicate node ID: {node_id}"
            )

        nodes[node_id] = item

    return buildings, junctions, nodes, edges


def validate_coordinates(node):
    try:
        lat = float(node["latitude"])
        lon = float(node["longitude"])
    except (TypeError, ValueError, KeyError):
        return False

    return (
        math.isfinite(lat)
        and math.isfinite(lon)
        and -90 <= lat <= 90
        and -180 <= lon <= 180
    )


def validate_graph(nodes, edges):
    problems = []
    seen = set()

    for node_id, node in nodes.items():
        if not validate_coordinates(node):
            problems.append(
                f"Invalid GPS coordinates: {node_id}"
            )

    for edge in edges:
        a = edge["from_id"]
        b = edge["to_id"]

        if a not in nodes or b not in nodes:
            problems.append(
                f"Unknown edge endpoint: {a} -> {b}"
            )

        if a == b:
            problems.append(
                f"Self-edge: {a}"
            )

        try:
            weight = float(edge["distance"])
            if not math.isfinite(weight) or weight <= 0:
                raise ValueError()
        except (TypeError, ValueError):
            problems.append(
                f"Invalid edge weight: {a} -> {b}"
            )

        if edge["path_type"] not in (
            "walking", "stairs"
        ):
            problems.append(
                f"Unknown path type: {a} -> {b}"
            )

        key = (a, b)

        if key in seen:
            problems.append(
                f"Duplicate directed edge: {a} -> {b}"
            )

        seen.add(key)

    return problems


def edge_allowed(edge, a, b, avoid_stairs):
    if avoid_stairs and edge["path_type"] == "stairs":
        return False

    return (
        (
            edge["from_id"] == a
            and edge["to_id"] == b
        )
        or (
            edge["bidirectional"]
            and edge["from_id"] == b
            and edge["to_id"] == a
        )
    )


def verify_result(
    nodes,
    edges,
    source,
    destination,
    path,
    used_edges,
    distance,
    avoid_stairs,
):
    problems = []

    if not path:
        return ["Empty path"]

    if path[0] != source:
        problems.append("Incorrect starting node")

    if path[-1] != destination:
        problems.append("Incorrect destination node")

    if len(path) != len(used_edges) + 1:
        problems.append("Path/edge length mismatch")

    if len(path) != len(set(path)):
        problems.append("Repeated node in shortest path")

    for node_id in path:
        if node_id not in nodes:
            problems.append(
                f"Unknown path node: {node_id}"
            )
        elif not validate_coordinates(nodes[node_id]):
            problems.append(
                f"Invalid path GPS: {node_id}"
            )

    calculated_distance = 0.0

    for index, edge in enumerate(used_edges):
        a = path[index]
        b = path[index + 1]

        if not edge_allowed(
            edge, a, b, avoid_stairs
        ):
            problems.append(
                f"Invalid connection: {a} -> {b}"
            )

        calculated_distance += float(
            edge["distance"]
        )

        if (
            avoid_stairs
            and edge["path_type"] == "stairs"
        ):
            problems.append(
                "Staircase used in stair-free route"
            )

    if (
        not math.isfinite(distance)
        or distance <= 0
    ):
        problems.append(
            "Invalid total distance"
        )

    if not math.isclose(
        calculated_distance,
        distance,
        rel_tol=1e-9,
        abs_tol=0.01,
    ):
        problems.append(
            "Total distance does not match edge sum"
        )

    # Check against every available direct edge.
    # A shortest path cannot cost more than a
    # direct eligible connection between endpoints.
    direct_weights = [
        float(edge["distance"])
        for edge in edges
        if edge_allowed(
            edge, source, destination,
            avoid_stairs
        )
    ]

    if direct_weights and (
        distance > min(direct_weights) + 0.01
    ):
        problems.append(
            "Route exceeds direct edge weight"
        )

    return problems


def run_tests():
    print("\nCAMPUSFLOW PHASE 9.8.6")
    print("=" * 45)

    buildings, junctions, nodes, edges = (
        load_test_data()
    )

    print("Buildings:", len(buildings))
    print("Junctions:", len(junctions))
    print("Total nodes:", len(nodes))
    print("Pedestrian edges:", len(edges))

    if (
        len(buildings) != 30
        or len(junctions) != 10
        or len(edges) != 59
    ):
        raise ValueError(
            "Unexpected graph size. "
            "Review the database before testing."
        )

    graph_problems = validate_graph(
        nodes, edges
    )

    if graph_problems:
        print("\nGraph validation failed:")

        for problem in graph_problems:
            print("-", problem)

        raise ValueError(
            "Fix graph validation errors first."
        )

    building_ids = [
        building["id"]
        for building in buildings
    ]

    results = []
    counters = Counter()

    pairs = list(
        permutations(building_ids, 2)
    )

    print("\nBuilding pairs:", len(pairs))
    print(
        "Planned route tests:",
        len(pairs) * 2
    )

    for source, destination in pairs:
        for avoid_stairs in (False, True):
            mode = (
                "stair_free"
                if avoid_stairs
                else "shortest"
            )

            counters["total"] += 1

            try:
                path, used_edges, distance = (
                    shortest_path(
                        nodes,
                        edges,
                        source,
                        destination,
                        avoid_stairs,
                    )
                )

                problems = verify_result(
                    nodes,
                    edges,
                    source,
                    destination,
                    path,
                    used_edges,
                    distance,
                    avoid_stairs,
                )

                contains_stairs = any(
                    edge["path_type"] == "stairs"
                    for edge in used_edges
                )

                if problems:
                    status = "FAIL"
                    counters["failed"] += 1
                else:
                    status = "PASS"
                    counters["passed"] += 1

                results.append({
                    "source": source,
                    "destination": destination,
                    "mode": mode,
                    "status": status,
                    "estimated_distance_m": round(
                        distance, 2
                    ),
                    "estimated_time_min": round(
                        distance / 75, 2
                    ),
                    "contains_stairs": contains_stairs,
                    "path": " -> ".join(path),
                    "issues": "; ".join(problems),
                })

            except Exception as error:
                counters["failed"] += 1

                results.append({
                    "source": source,
                    "destination": destination,
                    "mode": mode,
                    "status": "FAIL",
                    "estimated_distance_m": "",
                    "estimated_time_min": "",
                    "contains_stairs": "",
                    "path": "",
                    "issues": str(error),
                })

    columns = [
        "source",
        "destination",
        "mode",
        "status",
        "estimated_distance_m",
        "estimated_time_min",
        "contains_stairs",
        "path",
        "issues",
    ]

    with REPORT_PATH.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=columns,
        )

        writer.writeheader()
        writer.writerows(results)

    summary = [
        "CAMPUSFLOW ROUTE TEST SUMMARY",
        "=" * 45,
        f"Generated: {datetime.now().isoformat()}",
        f"Buildings: {len(buildings)}",
        f"Junctions: {len(junctions)}",
        f"Pedestrian edges: {len(edges)}",
        f"Total tests: {counters['total']}",
        f"Passed: {counters['passed']}",
        f"Failed: {counters['failed']}",
        (
            "Pass rate: "
            f"{counters['passed'] / counters['total'] * 100:.2f}%"
        ),
        "",
        "GPS distances are estimates.",
        "This does not verify real-world walkway geometry.",
    ]

    SUMMARY_PATH.write_text(
        "\n".join(summary),
        encoding="utf-8",
    )

    print("\nTEST RESULTS")
    print("=" * 45)

    for line in summary:
        print(line)

    print("\nCSV report:", REPORT_PATH)
    print("Summary:", SUMMARY_PATH)

    print("\nDatabase records were not modified.")

    if counters["failed"]:
        print(
            "\nSome tests failed. "
            "Review the CSV before continuing."
        )
        raise SystemExit(1)

    print("\nALL ROUTE TESTS PASSED!")


if __name__ == "__main__":
    try:
        run_tests()
    except Exception as error:
        print("Test execution failed:", error)
        raise SystemExit(1)
