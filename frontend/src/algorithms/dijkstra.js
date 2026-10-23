
export function dijkstra(locations, edges, start, end) {
  const distances = {};
  const previous = {};
  const unvisited = new Set();

  // Initialize every node
  for (const location of locations) {
    distances[location.id] = Infinity;
    previous[location.id] = null;
    unvisited.add(location.id);
  }

  if (!unvisited.has(start) || !unvisited.has(end)) {
    return null;
  }

  distances[start] = 0;

  // Build an undirected adjacency list
  const graph = {};

  for (const location of locations) {
    graph[location.id] = [];
  }

  for (const edge of edges) {
    if (
      !graph[edge.from] ||
      !graph[edge.to] ||
      !Number.isFinite(edge.distance) ||
      edge.distance < 0
    ) {
      throw new Error("Invalid campus edge");
    }

    graph[edge.from].push({
      node: edge.to,
      weight: edge.distance,
    });

    graph[edge.to].push({
      node: edge.from,
      weight: edge.distance,
    });
  }

  while (unvisited.size > 0) {
    let current = null;

    // Find the unvisited node with minimum distance
    for (const node of unvisited) {
      if (
        current === null ||
        distances[node] < distances[current]
      ) {
        current = node;
      }
    }

    if (current === null ||
        distances[current] === Infinity) {
      break;
    }

    if (current === end) break;

    unvisited.delete(current);

    for (const neighbor of graph[current]) {
      if (!unvisited.has(neighbor.node)) continue;

      const newDistance =
        distances[current] + neighbor.weight;

      if (newDistance < distances[neighbor.node]) {
        distances[neighbor.node] = newDistance;
        previous[neighbor.node] = current;
      }
    }
  }

  if (distances[end] === Infinity) {
    return null;
  }

  // Reconstruct the shortest route
  const path = [];
  let current = end;

  while (current !== null) {
    path.unshift(current);
    current = previous[current];
  }

  return {
    path,
    distance: distances[end],
  };
}
