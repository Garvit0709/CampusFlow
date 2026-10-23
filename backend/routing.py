
import heapq
import math


CROWD_PENALTIES = {
    "low": 0.0,
    "medium": 0.3,
    "high": 0.8,
}

WALKING_SPEED = 80


def find_shortest_route(
    start,
    end,
    locations,
    edges,
    crowd_levels=None,
    mode="shortest",
):
    """
    Dijkstra shortest-path algorithm.

    shortest:
        Minimize physical distance.

    smart:
        Minimize congestion-adjusted distance.

    Crowd data can come from either:
        - Live PostgreSQL reports
        - Machine learning predictions
    """

    if crowd_levels is None:
        crowd_levels = {}

    if mode not in ("shortest", "smart"):
        raise ValueError("Invalid routing mode")

    graph = {
        location["id"]: []
        for location in locations
    }

    if start not in graph or end not in graph:
        return None

    # Build bidirectional graph
    for edge in edges:
        source = edge["from"]
        destination = edge["to"]
        distance = edge["distance"]

        if source not in graph or destination not in graph:
            raise ValueError("Unknown campus location")

        if (
            not isinstance(distance, (int, float))
            or not math.isfinite(distance)
            or distance <= 0
        ):
            raise ValueError("Invalid edge distance")

        for origin, target in (
            (source, destination),
            (destination, source),
        ):
            crowd = crowd_levels.get(target, "low")

            if crowd not in CROWD_PENALTIES:
                raise ValueError("Invalid crowd level")

            penalty = CROWD_PENALTIES[crowd]

            cost = (
                distance
                if mode == "shortest"
                else distance * (1 + penalty)
            )

            graph[origin].append({
                "node": target,
                "distance": distance,
                "cost": cost,
                "crowd": crowd,
            })

    distances = {
        node: float("inf")
        for node in graph
    }

    previous = {
        node: None
        for node in graph
    }

    previous_edge = {}

    distances[start] = 0
    queue = [(0, start)]

    while queue:
        current_cost, current = heapq.heappop(queue)

        if current_cost > distances[current]:
            continue

        if current == end:
            break

        for edge in graph[current]:
            neighbor = edge["node"]
            new_cost = current_cost + edge["cost"]

            if new_cost < distances[neighbor]:
                distances[neighbor] = new_cost
                previous[neighbor] = current
                previous_edge[neighbor] = edge

                heapq.heappush(
                    queue,
                    (new_cost, neighbor)
                )

    if distances[end] == float("inf"):
        return None

    # Reconstruct route
    path = []
    current = end
    total_distance = 0

    while current is not None:
        path.append(current)

        if current in previous_edge:
            total_distance += (
                previous_edge[current]["distance"]
            )

        current = previous[current]

    path.reverse()

    route_crowds = [
        crowd_levels.get(node, "low")
        for node in path[1:]
    ]

    if "high" in route_crowds:
        crowd_summary = "high"
    elif "medium" in route_crowds:
        crowd_summary = "medium"
    else:
        crowd_summary = "low"

    return {
        "path": path,
        "distance": total_distance,
        "estimated_time": math.ceil(
            distances[end] / WALKING_SPEED
        ),
        "weighted_cost": round(distances[end], 2),
        "crowd_level": crowd_summary,
        "mode": mode,
    }
