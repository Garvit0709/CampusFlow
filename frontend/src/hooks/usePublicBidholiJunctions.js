
import { useEffect, useState } from "react";

const API_URL = (
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000"
).replace(/\/$/, "");

export default function usePublicBidholiJunctions() {
  const [junctions, setJunctions] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    const controller = new AbortController();

    async function loadJunctions() {
      try {
        const response = await fetch(
          `${API_URL}/bidholi/pedestrian-graph`,
          { signal: controller.signal }
        );

        if (!response.ok) {
          throw new Error(
            `Graph request failed: ${response.status}`
          );
        }

        const data = await response.json();

        if (!Array.isArray(data.nodes)) {
          throw new Error("Invalid graph response");
        }

        const validJunctions = data.nodes
          .filter((node) => node.node_type === "junction")
          .map((node) => ({
            id: node.id,
            name: node.name,
            latitude: Number(node.latitude),
            longitude: Number(node.longitude),
          }))
          .filter(
            (node) =>
              Number.isFinite(node.latitude) &&
              Number.isFinite(node.longitude)
          );

        setJunctions(validJunctions);
        setError(null);
      } catch (err) {
        if (err.name !== "AbortError") {
          setError(err.message);
        }
      }
    }

    loadJunctions();

    return () => controller.abort();
  }, []);

  return { junctions, error };
}
