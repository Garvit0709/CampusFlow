
"""
CampusFlow Phase 9.9.2
Bidholi Pedestrian Routing Benchmark

Read-only benchmark:
- PostgreSQL graph loading
- Dijkstra shortest route
- Dijkstra stair-free route
- Combined routing performance

Does not modify PostgreSQL.
"""

import statistics
import time
from pathlib import Path

from bidholi_pedestrian_routing import (
    load_graph,
    shortest_path,
)

RUNS = 100

SOURCE = "bidholi-22"
DESTINATION = "bidholi-8"

REPORT_FILE = (
    Path(__file__).resolve().parent
    / "bidholi_performance_report.txt"
)


def milliseconds(start):
    return (time.perf_counter() - start) * 1000


def summarize(values):
    ordered = sorted(values)

    p95_index = min(
        len(ordered) - 1,
        max(0, int(len(ordered) * 0.95) - 1)
    )

    return {
        "average": statistics.mean(values),
        "median": statistics.median(values),
        "minimum": min(values),
        "maximum": max(values),
        "p95": ordered[p95_index],
    }


def benchmark():
    print("\nCAMPUSFLOW ROUTING BENCHMARK")
    print("=" * 45)

    print("Iterations:", RUNS)
    print("Source:", SOURCE)
    print("Destination:", DESTINATION)

    load_times = []
    shortest_times = []
    stairfree_times = []
    combined_times = []

    # Warm-up
    nodes, edges = load_graph()

    shortest_path(
        nodes, edges,
        SOURCE, DESTINATION, False
    )

    shortest_path(
        nodes, edges,
        SOURCE, DESTINATION, True
    )

    for index in range(RUNS):

        start = time.perf_counter()
        nodes, edges = load_graph()
        load_times.append(milliseconds(start))

        start = time.perf_counter()
        shortest_path(
            nodes, edges,
            SOURCE, DESTINATION, False
        )
        shortest_times.append(milliseconds(start))

        start = time.perf_counter()
        shortest_path(
            nodes, edges,
            SOURCE, DESTINATION, True
        )
        stairfree_times.append(milliseconds(start))

        start = time.perf_counter()
        nodes, edges = load_graph()

        shortest_path(
            nodes, edges,
            SOURCE, DESTINATION, False
        )

        shortest_path(
            nodes, edges,
            SOURCE, DESTINATION, True
        )

        combined_times.append(milliseconds(start))

        if (index + 1) % 20 == 0:
            print(
                f"Completed {index + 1}/{RUNS}"
            )

    results = {
        "Graph loading": summarize(load_times),
        "Shortest Dijkstra": summarize(shortest_times),
        "Stair-free Dijkstra": summarize(stairfree_times),
        "Combined operation": summarize(combined_times),
    }

    lines = [
        "CAMPUSFLOW PERFORMANCE REPORT",
        "=" * 55,
        f"Iterations: {RUNS}",
        f"Source: {SOURCE}",
        f"Destination: {DESTINATION}",
        "",
    ]

    for name, values in results.items():
        lines.append(name)

        for metric, value in values.items():
            lines.append(
                f"  {metric}: {value:.3f} ms"
            )

        lines.append("")

    lines.append(
        "Measured locally; not an HTTP network benchmark."
    )

    REPORT_FILE.write_text(
        "\n".join(lines),
        encoding="utf-8"
    )

    print("\n" + "\n".join(lines))
    print("Report saved:", REPORT_FILE)


if __name__ == "__main__":
    benchmark()
