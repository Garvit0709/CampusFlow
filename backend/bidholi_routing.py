
# ============================================================
# CAMPUSFLOW - UPES BIDHOLI ROUTING
# Phase 9.5
#
# PostgreSQL + FastAPI + Dijkstra
# GPS-based estimated walking distances
# Supports Avoid Stairs
#
# Does not modify existing demo campus routing.
# ============================================================

import heapq
import math
import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


# ============================================================
# ENVIRONMENT CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")

router = APIRouter(
    prefix="/bidholi",
    tags=["UPES Bidholi"]
)


# ============================================================
# DATABASE CONNECTION
# ============================================================

def connect():
    try:
        return psycopg.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            port=int(os.getenv("DB_PORT", "5432")),
            dbname=os.getenv("DB_NAME", "campusflow_db"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD"),
            row_factory=dict_row,
        )

    except psycopg.Error:
        raise HTTPException(
            status_code=503,
            detail="Bidholi database unavailable"
        )


# ============================================================
# REQUEST MODEL
# ============================================================

class RouteRequest(BaseModel):
    source: str = Field(min_length=1)
    destination: str = Field(min_length=1)
    avoid_stairs: bool = False


# ============================================================
# DATABASE READ HELPERS
# ============================================================

def load_locations():
    with connect() as conn:
        return conn.execute("""
            SELECT
                id,
                name,
                category,
                latitude,
                longitude,
                image_url,
                verified_entrance
            FROM bidholi_locations
            ORDER BY name
        """).fetchall()


def load_edges():
    with connect() as conn:
        return conn.execute("""
            SELECT
                id,
                from_id,
                to_id,
                distance,
                direct_distance,
                path_factor,
                path_type,
                distance_type,
                verified_connection,
                bidirectional
            FROM bidholi_edges
            ORDER BY id
        """).fetchall()


# ============================================================
# GET ALL BIDHOLI LOCATIONS
# ============================================================

@router.get("/locations")
def locations():
    try:
        return load_locations()

    except psycopg.Error:
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve Bidholi locations"
        )


# ============================================================
# GET ALL BIDHOLI EDGES
# ============================================================

@router.get("/edges")
def edges():
    try:
        return load_edges()

    except psycopg.Error:
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve Bidholi edges"
        )


# ============================================================
# DIJKSTRA SHORTEST PATH ALGORITHM
# ============================================================

def calculate_shortest_path(
    nodes,
    edges_data,
    source,
    destination,
    avoid_stairs=False
):

    # Validate source and destination.

    if source not in nodes:
        raise HTTPException(
            status_code=404,
            detail="Starting location not found"
        )

    if destination not in nodes:
        raise HTTPException(
            status_code=404,
            detail="Destination location not found"
        )

    # Handle identical source and destination.

    if source == destination:
        return {
            "path": [source],
            "used_edges": [],
            "distance": 0.0,
        }

    # Initialize graph.

    graph = {
        node_id: []
        for node_id in nodes
    }

    # Add pedestrian connections.

    for edge in edges_data:

        path_type = edge["path_type"]

        # Exclude staircase connections if requested.

        if avoid_stairs and path_type == "stairs":
            continue

        start = edge["from_id"]
        end = edge["to_id"]

        distance = float(edge["distance"])

        if (
            start not in graph
            or end not in graph
            or not math.isfinite(distance)
            or distance <= 0
        ):
            continue

        # Forward connection.

        graph[start].append(
            (end, distance, edge)
        )

        # Reverse connection only when permitted.

        if edge["bidirectional"]:
            graph[end].append(
                (start, distance, edge)
            )

    # Dijkstra initialization.

    best = {
        source: 0.0
    }

    previous = {}

    queue = [
        (0.0, source)
    ]

    # Find shortest route.

    while queue:

        current_distance, current_node = (
            heapq.heappop(queue)
        )

        if current_distance > best.get(
            current_node, math.inf
        ):
            continue

        if current_node == destination:
            break

        for neighbor, weight, edge in graph[current_node]:

            new_distance = (
                current_distance + weight
            )

            if new_distance < best.get(
                neighbor, math.inf
            ):

                best[neighbor] = new_distance

                previous[neighbor] = (
                    current_node,
                    edge
                )

                heapq.heappush(
                    queue,
                    (new_distance, neighbor)
                )

    # No connected route found.

    if destination not in best:
        raise HTTPException(
            status_code=404,
            detail=(
                "No connected walking route found. "
                "Some campus paths are not mapped yet."
            )
        )

    # Reconstruct route.

    path = [destination]

    used_edges = []

    current = destination

    while current != source:

        parent, edge = previous[current]

        used_edges.append(edge)

        path.append(parent)

        current = parent

    path.reverse()

    used_edges.reverse()

    return {
        "path": path,
        "used_edges": used_edges,
        "distance": best[destination],
    }


# ============================================================
# POST: CALCULATE BIDHOLI ROUTE
# ============================================================

@router.post("/route")
def route(request: RouteRequest):

    # Load PostgreSQL data.

    try:
        locations_data = load_locations()
        edges_data = load_edges()

    except psycopg.Error:
        raise HTTPException(
            status_code=503,
            detail="Unable to load Bidholi routing data"
        )

    # Create location lookup.

    nodes = {
        location["id"]: location
        for location in locations_data
    }

    # Execute Dijkstra.

    result = calculate_shortest_path(
        nodes=nodes,
        edges_data=edges_data,
        source=request.source,
        destination=request.destination,
        avoid_stairs=request.avoid_stairs,
    )

    path = result["path"]

    used_edges = result["used_edges"]

    distance = round(
        result["distance"], 1
    )

    # Approximate walking speed:
    # 75 metres per minute.

    walking_speed_m_per_min = 75.0

    estimated_time = round(
        distance / walking_speed_m_per_min,
        1
    )

    # Determine whether the route uses provisional edges.

    contains_provisional_edges = any(
        not edge["verified_connection"]
        for edge in used_edges
    )

    # Determine whether the route includes stairs.

    contains_stairs = any(
        edge["path_type"] == "stairs"
        for edge in used_edges
    )

    # Collect path types.

    path_types = [
        edge["path_type"]
        for edge in used_edges
    ]

    # Create route coordinates.

    coordinates = [
        [
            nodes[node_id]["latitude"],
            nodes[node_id]["longitude"]
        ]
        for node_id in path
    ]

    # Return frontend-compatible response.

    return {
        "campus": "UPES Bidholi",

        "routing_algorithm": "dijkstra",

        "source": request.source,

        "destination": request.destination,

        "path": path,

        "path_names": [
            nodes[node_id]["name"]
            for node_id in path
        ],

        "coordinates": coordinates,

        "path_coordinates": coordinates,

        "estimated_distance_m": distance,

        "distance": distance,

        "estimated_time_min": estimated_time,

        "estimated_time": estimated_time,

        "avoid_stairs": request.avoid_stairs,

        "contains_stairs": contains_stairs,

        "contains_provisional_edges": (
            contains_provisional_edges
        ),

        "path_types": path_types,

        "distance_type": "estimated",

        "distance_source": (
            "GPS straight-line distances multiplied "
            "by assumed path adjustment factors. "
            "Not measured walking distances."
        ),

        "geometry_warning": (
            "Route lines connect recorded GPS points. "
            "Actual walking paths, road turns and "
            "building entrances are not yet surveyed."
        ),
    }
