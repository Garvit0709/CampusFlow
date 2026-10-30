import heapq
import math
import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

load_dotenv(Path(__file__).resolve().parent / ".env")

router = APIRouter(
    prefix="/bidholi",
    tags=["UPES Bidholi Pedestrian Routing"]
)


class PedestrianRouteRequest(BaseModel):
    source: str = Field(min_length=1)
    destination: str = Field(min_length=1)
    avoid_stairs: bool = False


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
    except psycopg.Error as exc:
        raise HTTPException(
            status_code=503,
            detail="Pedestrian database unavailable"
        ) from exc


def load_graph():
    try:
        with connect() as conn:

            buildings = conn.execute("""
                SELECT id, name, latitude, longitude
                FROM bidholi_locations
            """).fetchall()

            junctions = conn.execute("""
                SELECT id, name, latitude, longitude
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
            detail="Unable to load pedestrian graph"
        ) from exc

    nodes = {}

    for building in buildings:
        nodes[building["id"]] = {
            **building,
            "node_type": "building"
        }

    for junction in junctions:
        if junction["id"] in nodes:
            raise HTTPException(
                status_code=500,
                detail="Duplicate pedestrian node ID"
            )

        nodes[junction["id"]] = {
            **junction,
            "node_type": "junction"
        }

    return nodes, edges


def shortest_path(
    nodes,
    edges,
    source,
    destination,
    avoid_stairs=False
):
    if source not in nodes:
        raise HTTPException(
            status_code=404,
            detail="Starting location not found"
        )

    if destination not in nodes:
        raise HTTPException(
            status_code=404,
            detail="Destination not found"
        )

    graph = {node_id: [] for node_id in nodes}

    for edge in edges:
        if avoid_stairs and edge["path_type"] == "stairs":
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
                detail="Invalid pedestrian graph edge"
            )

        graph[start].append((end, weight, edge))

        if edge["bidirectional"]:
            graph[end].append((start, weight, edge))

    distances = {source: 0.0}
    previous = {}
    queue = [(0.0, source)]

    while queue:
        cost, current = heapq.heappop(queue)

        if cost > distances.get(current, math.inf):
            continue

        if current == destination:
            break

        for neighbor, weight, edge in graph[current]:
            new_cost = cost + weight

            if new_cost < distances.get(neighbor, math.inf):
                distances[neighbor] = new_cost
                previous[neighbor] = (current, edge)

                heapq.heappush(
                    queue,
                    (new_cost, neighbor)
                )

    if destination not in distances:
        raise HTTPException(
            status_code=404,
            detail="No connected pedestrian route found"
        )

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

    return path, used_edges, distances[destination]


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


@router.post("/pedestrian-route")
def calculate_pedestrian_route(
    request: PedestrianRouteRequest
):
    nodes, edges = load_graph()

    path, used_edges, distance = shortest_path(
        nodes,
        edges,
        request.source,
        request.destination,
        request.avoid_stairs
    )

    coordinates = [
        [
            float(nodes[node_id]["latitude"]),
            float(nodes[node_id]["longitude"])
        ]
        for node_id in path
    ]

    total_distance = round(distance, 1)

    # Estimated walking speed: 75 metres/minute.
    walking_minutes = round(
        total_distance / 75.0, 1
    )

    contains_stairs = any(
        edge["path_type"] == "stairs"
        for edge in used_edges
    )

    contains_provisional = any(
        not edge["verified_connection"]
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

        "contains_unverified_geometry": any(
            not edge["geometry_verified"]
            for edge in used_edges
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
