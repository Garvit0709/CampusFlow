
# ============================================================
# CampusFlow Phase 9.9.2.3
# UPES Bidholi Pedestrian Routing + Thread-Safe Graph Cache
# ============================================================

import heapq
import math
import os
import threading
import time

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


# ============================================================
# FASTAPI ROUTER
# ============================================================

router = APIRouter(
    prefix="/bidholi",
    tags=["UPES Bidholi Pedestrian Routing"],
)


class PedestrianRouteRequest(BaseModel):
    source: str = Field(min_length=1)
    destination: str = Field(min_length=1)
    avoid_stairs: bool = False


# ============================================================
# CACHE CONFIGURATION
# ============================================================

GRAPH_CACHE_TTL = 30.0

_graph_cache = {
    "nodes": None,
    "edges": None,
    "expires_at": 0.0,
}

_graph_cache_lock = threading.Lock()


def clear_graph_cache():
    """
    Manually invalidate the pedestrian graph cache.

    The next request reloads graph data from PostgreSQL.
    """

    with _graph_cache_lock:
        _graph_cache["nodes"] = None
        _graph_cache["edges"] = None
        _graph_cache["expires_at"] = 0.0


# ============================================================
# POSTGRESQL CONNECTION
# ============================================================

def connect():
    try:
        return psycopg.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            port=int(os.getenv("DB_PORT", "5432")),
            dbname=os.getenv(
                "DB_NAME",
                "campusflow_db",
            ),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD"),
            row_factory=dict_row,
        )

    except psycopg.Error as exc:
        raise HTTPException(
            status_code=503,
            detail="Pedestrian database unavailable",
        ) from exc


# ============================================================
# GRAPH LOADING WITH THREAD-SAFE CACHE
# ============================================================

def load_graph():
    """
    Load the pedestrian graph from PostgreSQL.

    Returns cached graph data when available.

    Cache TTL: 30 seconds.

    Thread-safe within a single Python process.

    Returned graph data must be treated as read-only.
    """

    with _graph_cache_lock:

        current_time = time.monotonic()

        cache_valid = (
            _graph_cache["nodes"] is not None
            and _graph_cache["edges"] is not None
            and current_time < _graph_cache["expires_at"]
        )

        if cache_valid:
            return (
                _graph_cache["nodes"],
                _graph_cache["edges"],
            )

        try:
            with connect() as conn:

                buildings = conn.execute("""
                    SELECT
                        id,
                        name,
                        latitude,
                        longitude
                    FROM bidholi_locations
                """).fetchall()

                junctions = conn.execute("""
                    SELECT
                        id,
                        name,
                        latitude,
                        longitude
                    FROM bidholi_junctions
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
                """).fetchall()

        except psycopg.Error as exc:
            raise HTTPException(
                status_code=503,
                detail="Unable to load pedestrian graph",
            ) from exc

        # ----------------------------------------
        # BUILD NODE DICTIONARY
        # ----------------------------------------

        nodes = {}

        for building in buildings:

            node_id = building["id"]

            if node_id in nodes:
                raise HTTPException(
                    status_code=500,
                    detail="Duplicate pedestrian node ID",
                )

            nodes[node_id] = {
                **building,
                "node_type": "building",
            }

        for junction in junctions:

            node_id = junction["id"]

            if node_id in nodes:
                raise HTTPException(
                    status_code=500,
                    detail="Duplicate pedestrian node ID",
                )

            nodes[node_id] = {
                **junction,
                "node_type": "junction",
            }

        # ----------------------------------------
        # VALIDATE GRAPH EDGES
        # ----------------------------------------

        for edge in edges:

            start = edge["from_id"]
            end = edge["to_id"]

            if start not in nodes or end not in nodes:
                raise HTTPException(
                    status_code=500,
                    detail="Pedestrian graph contains unknown nodes",
                )

            weight = float(edge["distance"])

            if (
                not math.isfinite(weight)
                or weight <= 0
            ):
                raise HTTPException(
                    status_code=500,
                    detail="Invalid pedestrian edge distance",
                )

        # ----------------------------------------
        # ATOMIC CACHE UPDATE
        # ----------------------------------------

        _graph_cache["nodes"] = nodes
        _graph_cache["edges"] = edges

        _graph_cache["expires_at"] = (
            time.monotonic() + GRAPH_CACHE_TTL
        )

        return nodes, edges


# ============================================================
# DIJKSTRA SHORTEST PATH
# ============================================================

def shortest_path(
    nodes,
    edges,
    source,
    destination,
    avoid_stairs=False,
):
    """
    Calculate the shortest pedestrian route.

    Supports:
    - Bidirectional walking connections
    - Staircase avoidance
    - Estimated distance weights
    """

    if source not in nodes:
        raise HTTPException(
            status_code=404,
            detail="Starting location not found",
        )

    if destination not in nodes:
        raise HTTPException(
            status_code=404,
            detail="Destination not found",
        )

    graph = {
        node_id: []
        for node_id in nodes
    }

    # ----------------------------------------
    # BUILD ADJACENCY LIST
    # ----------------------------------------

    for edge in edges:

        if (
            avoid_stairs
            and edge["path_type"] == "stairs"
        ):
            continue

        start = edge["from_id"]
        end = edge["to_id"]

        weight = float(edge["distance"])

        if (
            start not in graph
            or end not in graph
            or not math.isfinite(weight)
            or weight <= 0
        ):
            raise HTTPException(
                status_code=500,
                detail="Invalid pedestrian graph edge",
            )

        graph[start].append(
            (end, weight, edge)
        )

        if edge["bidirectional"]:
            graph[end].append(
                (start, weight, edge)
            )

    # ----------------------------------------
    # INITIALIZE DIJKSTRA
    # ----------------------------------------

    distances = {
        source: 0.0
    }

    previous = {}

    queue = [
        (0.0, source)
    ]

    # ----------------------------------------
    # SHORTEST PATH SEARCH
    # ----------------------------------------

    while queue:

        cost, current = heapq.heappop(queue)

        if cost > distances.get(
            current,
            math.inf,
        ):
            continue

        if current == destination:
            break

        for neighbor, weight, edge in graph[current]:

            new_cost = cost + weight

            if new_cost < distances.get(
                neighbor,
                math.inf,
            ):

                distances[neighbor] = new_cost

                previous[neighbor] = (
                    current,
                    edge,
                )

                heapq.heappush(
                    queue,
                    (new_cost, neighbor),
                )

    if destination not in distances:
        raise HTTPException(
            status_code=404,
            detail="No connected pedestrian route found",
        )

    # ----------------------------------------
    # RECONSTRUCT PATH
    # ----------------------------------------

    path = [
        destination
    ]

    used_edges = []

    current = destination

    while current != source:

        parent, edge = previous[current]

        used_edges.append(edge)
        path.append(parent)

        current = parent

    path.reverse()
    used_edges.reverse()

    return (
        path,
        used_edges,
        distances[destination],
    )


# ============================================================
# GET PEDESTRIAN GRAPH
# ============================================================

@router.get("/pedestrian-graph")
def get_pedestrian_graph():

    nodes, edges = load_graph()

    return {
        "campus": "UPES Bidholi",
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "nodes": list(nodes.values()),
        "edges": edges,
        "distance_type": "estimated",
        "geometry_verified": False,
    }


# ============================================================
# POST PEDESTRIAN ROUTE
# ============================================================

@router.post("/pedestrian-route")
def calculate_pedestrian_route(
    request: PedestrianRouteRequest,
):

    nodes, edges = load_graph()

    path, used_edges, distance = shortest_path(
        nodes,
        edges,
        request.source,
        request.destination,
        request.avoid_stairs,
    )

    coordinates = [
        [
            float(nodes[node_id]["latitude"]),
            float(nodes[node_id]["longitude"]),
        ]
        for node_id in path
    ]

    total_distance = round(
        distance,
        1,
    )

    walking_minutes = round(
        total_distance / 75.0,
        1,
    )

    contains_stairs = any(
        edge["path_type"] == "stairs"
        for edge in used_edges
    )

    contains_provisional = any(
        not edge["verified_connection"]
        for edge in used_edges
    )

    contains_unverified_geometry = any(
        not edge["geometry_verified"]
        for edge in used_edges
    )

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

        "estimated_distance_m": total_distance,
        "distance": total_distance,

        "estimated_time_min": walking_minutes,
        "estimated_time": walking_minutes,

        "avoid_stairs": request.avoid_stairs,
        "contains_stairs": contains_stairs,

        "contains_provisional_edges": (
            contains_provisional
        ),

        "contains_unverified_geometry": (
            contains_unverified_geometry
        ),

        "path_types": [
            edge["path_type"]
            for edge in used_edges
        ],

        "path_node_types": [
            nodes[node_id]["node_type"]
            for node_id in path
        ],

        "distance_type": "estimated",

        "distance_source": (
            "GPS-based straight-line distances "
            "with assumed path factors."
        ),

        "geometry_warning": (
            "Junctions were positioned manually. "
            "Displayed route segments are approximations, "
            "not surveyed pedestrian geometry."
        ),
    }
