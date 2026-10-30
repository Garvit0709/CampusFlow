
import { useEffect, useRef, useState } from "react";
import {
  CircleMarker,
  Marker,
  Polyline,
  Popup,
  useMap,
} from "react-leaflet";
import L from "leaflet";

import BidholiWalkingDirections from "./BidholiWalkingDirections";

const API_URL = (
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000"
).replace(/\/$/, "");

const ROUTE_API = `${API_URL}/bidholi/pedestrian-route`;

// =====================================================
// MAP UTILITIES
// =====================================================

function getPositions(route) {
  const coordinates =
    route?.path_coordinates ||
    route?.coordinates ||
    [];

  if (!Array.isArray(coordinates)) return [];

  return coordinates.map((point) => {
    if (!Array.isArray(point) || point.length < 2) {
      return null;
    }

    const lat = Number(point[0]);
    const lon = Number(point[1]);

    if (
      !Number.isFinite(lat) ||
      !Number.isFinite(lon) ||
      Math.abs(lat) > 90 ||
      Math.abs(lon) > 180
    ) {
      return null;
    }

    return [lat, lon];
  }).filter(Boolean);
}

function makePin(label, type) {
  return L.divIcon({
    className: "cf-navigation-icon",
    html: `
      <div class="cf-nav-pin cf-nav-${type}">
        ${label}
      </div>
    `,
    iconSize: [34, 34],
    iconAnchor: [17, 17],
    popupAnchor: [0, -18],
  });
}

const START_ICON = makePin("S", "start");
const END_ICON = makePin("D", "end");

function makeArrow(angle, color) {
  return L.divIcon({
    className: "cf-route-arrow-icon",
    html: `
      <div
        class="cf-route-arrow"
        style="
          --arrow-angle:${angle}deg;
          --arrow-color:${color};
        "
      >
        <svg
          viewBox="0 0 24 24"
          width="23"
          height="23"
          aria-hidden="true"
        >
          <path
            d="M4 12H19M13 6L19 12L13 18"
            fill="none"
            stroke="white"
            stroke-width="3"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
      </div>
    `,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
  });
}

// =====================================================
// LEAFLET ROUTE OVERLAY
// Preserves Phase 9.8.3 visual navigation.
// =====================================================

export function BidholiRouteLine({ route }) {
  const map = useMap();
  const positions = getPositions(route);

  useEffect(() => {
    if (positions.length < 2) return;

    map.fitBounds(positions, {
      padding: [60, 60],
      maxZoom: 19,
      animate: true,
    });
  }, [map, route]);

  if (!route || positions.length === 0) {
    return null;
  }

  const color = route.contains_stairs
    ? "#ea580c"
    : "#16a34a";

  const firstPoint = positions[0];
  const lastPoint = positions[positions.length - 1];

  const arrows = [];

  for (let i = 0; i < positions.length - 1; i++) {
    const start = positions[i];
    const end = positions[i + 1];

    const a = map.project(start, map.getZoom());
    const b = map.project(end, map.getZoom());

    const angle =
      Math.atan2(b.y - a.y, b.x - a.x) *
      180 / Math.PI;

    arrows.push({
      id: i,
      position: [
        (start[0] + end[0]) / 2,
        (start[1] + end[1]) / 2,
      ],
      angle,
    });
  }

  return (
    <>
      {positions.length >= 2 && (
        <>
          <Polyline
            positions={positions}
            pathOptions={{
              color: "#ffffff",
              weight: 11,
              opacity: 0.9,
            }}
          />

          <Polyline
            positions={positions}
            pathOptions={{
              color,
              weight: 6,
              opacity: 0.95,
              lineCap: "round",
              lineJoin: "round",
            }}
          />
        </>
      )}

      {arrows.map((arrow) => (
        <Marker
          key={arrow.id}
          position={arrow.position}
          icon={makeArrow(arrow.angle, color)}
          interactive={false}
          keyboard={false}
          zIndexOffset={450}
        />
      ))}

      {route.path?.map((nodeId, index) => {
        if (
          route.path_node_types?.[index] !==
          "junction" ||
          !positions[index]
        ) {
          return null;
        }

        return (
          <CircleMarker
            key={`${nodeId}-${index}`}
            center={positions[index]}
            radius={9}
            pathOptions={{
              color: "#ffffff",
              fillColor: "#f59e0b",
              fillOpacity: 1,
              weight: 3,
            }}
          >
            <Popup>
              <strong>{nodeId}</strong>
              <p>{route.path_names?.[index]}</p>
              <small>
                Junction geometry not ground verified.
              </small>
            </Popup>
          </CircleMarker>
        );
      })}

      <Marker
        position={firstPoint}
        icon={START_ICON}
        zIndexOffset={1000}
      >
        <Popup>
          <strong>Starting Point</strong>
          <p>{route.path_names?.[0]}</p>
        </Popup>
      </Marker>

      <Marker
        position={lastPoint}
        icon={END_ICON}
        zIndexOffset={1000}
      >
        <Popup>
          <strong>Destination</strong>
          <p>
            {route.path_names?.[
              route.path_names.length - 1
            ]}
          </p>
        </Popup>
      </Marker>
    </>
  );
}

// =====================================================
// API HELPER
// =====================================================

async function requestRoute(
  source,
  destination,
  avoidStairs,
  signal
) {
  const response = await fetch(ROUTE_API, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    signal,
    body: JSON.stringify({
      source,
      destination,
      avoid_stairs: avoidStairs,
    }),
  });

  let data;

  try {
    data = await response.json();
  } catch {
    throw new Error("Invalid API response.");
  }

  if (!response.ok) {
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : "Unable to calculate route."
    );
  }

  if (
    !Array.isArray(data.path) ||
    !Array.isArray(data.path_coordinates) ||
    data.path.length !== data.path_coordinates.length
  ) {
    throw new Error("Incomplete route data.");
  }

  return data;
}

function sameRoute(a, b) {
  return (
    a &&
    b &&
    JSON.stringify(a.path) ===
      JSON.stringify(b.path)
  );
}

// =====================================================
// ROUTE COMPARISON CARD
// =====================================================

function RouteCard({
  title,
  route,
  selected,
  onSelect,
  type,
  unavailable,
}) {
  if (!route) {
    return (
      <div className="cf-comparison-card unavailable">
        <h3>{title}</h3>
        <p>{unavailable || "Route unavailable."}</p>
      </div>
    );
  }

  return (
    <div
      className={
        "cf-comparison-card " +
        (selected ? "active " : "") +
        type
      }
    >
      <div className="cf-comparison-card-header">
        <h3>{title}</h3>

        {selected && (
          <span className="cf-selected-label">
            Selected
          </span>
        )}
      </div>

      <div className="cf-comparison-distance">
        {route.estimated_distance_m} m
      </div>

      <p className="cf-comparison-time">
        Approx. {route.estimated_time_min} min
      </p>

      <span
        className={
          "cf-comparison-stairs " +
          (route.contains_stairs
            ? "has-stairs"
            : "no-stairs")
        }
      >
        {route.contains_stairs
          ? "Includes stairs"
          : "No stairs"}
      </span>

      <p className="cf-comparison-path">
        {route.path_names?.join(" → ")}
      </p>

      <button
        type="button"
        className="cf-select-route"
        onClick={onSelect}
        disabled={selected}
      >
        {selected ? "Showing on Map" : "Show This Route"}
      </button>
    </div>
  );
}

// =====================================================
// MAIN ROUTING PANEL
// =====================================================

export default function BidholiRoutingPanel({
  locations = [],
  onRoute,
}) {
  const [source, setSource] = useState("");
  const [destination, setDestination] = useState("");

  const [shortestRoute, setShortestRoute] =
    useState(null);

  const [stairFreeRoute, setStairFreeRoute] =
    useState(null);

  const [selectedMode, setSelectedMode] =
    useState("shortest");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [stairFreeError, setStairFreeError] =
    useState("");

  const requestRef = useRef(null);

  const selectedRoute =
    selectedMode === "stairfree"
      ? stairFreeRoute
      : shortestRoute;

  function clearResults() {
    requestRef.current?.abort();
    requestRef.current = null;

    setLoading(false);
    setError("");
    setStairFreeError("");

    setShortestRoute(null);
    setStairFreeRoute(null);
    setSelectedMode("shortest");

    onRoute?.(null);
  }

  useEffect(() => {
    return () => {
      requestRef.current?.abort();
    };
  }, []);

  async function compareRoutes() {
    if (!source || !destination) {
      setError("Select both locations.");
      return;
    }

    if (source === destination) {
      setError("Choose different locations.");
      return;
    }

    clearResults();

    const controller = new AbortController();
    requestRef.current = controller;

    setLoading(true);

    try {
      const results = await Promise.allSettled([
        requestRoute(
          source,
          destination,
          false,
          controller.signal
        ),
        requestRoute(
          source,
          destination,
          true,
          controller.signal
        ),
      ]);

      if (controller.signal.aborted) return;

      const shortest =
        results[0].status === "fulfilled"
          ? results[0].value
          : null;

      const stairFree =
        results[1].status === "fulfilled"
          ? results[1].value
          : null;

      if (!shortest && !stairFree) {
        setError(
          "Neither route could be calculated. " +
          "Check your API and pedestrian graph."
        );
        return;
      }

      setShortestRoute(shortest);
      setStairFreeRoute(stairFree);

      if (!stairFree) {
        setStairFreeError(
          results[1].reason?.message ||
          "No stair-free route available."
        );
      }

      const initialMode = shortest
        ? "shortest"
        : "stairfree";

      setSelectedMode(initialMode);
      onRoute?.(shortest || stairFree);
    } catch (err) {
      if (!controller.signal.aborted) {
        setError(err.message || "Routing failed.");
      }
    } finally {
      if (requestRef.current === controller) {
        requestRef.current = null;
        setLoading(false);
      }
    }
  }

  function selectRoute(mode) {
    const route =
      mode === "stairfree"
        ? stairFreeRoute
        : shortestRoute;

    if (!route) return;

    setSelectedMode(mode);
    onRoute?.(route);
  }

  const identicalRoutes = sameRoute(
    shortestRoute,
    stairFreeRoute
  );

  const distanceDifference =
    shortestRoute && stairFreeRoute
      ? Math.max(
          0,
          Math.round(
            stairFreeRoute.estimated_distance_m -
            shortestRoute.estimated_distance_m
          )
        )
      : null;

  return (
    <section className="bidholi-routing-panel">
      <div className="bidholi-routing-heading">
        <div>
          <span className="bidholi-eyebrow">
            CAMPUSFLOW SMART NAVIGATION
          </span>

          <h2>Compare Walking Routes</h2>

          <p>
            Compare shortest and stair-free routes
            across the UPES Bidholi pedestrian network.
          </p>
        </div>

        <span className="bidholi-routing-tag">
          Dijkstra
        </span>
      </div>

      <div className="bidholi-routing-fields">
        <label>
          Starting Location
          <select
            value={source}
            onChange={(event) => {
              setSource(event.target.value);
              clearResults();
            }}
          >
            <option value="">
              Select starting point
            </option>

            {locations.map((location) => (
              <option
                key={location.id}
                value={location.id}
              >
                {location.name}
              </option>
            ))}
          </select>
        </label>

        <label>
          Destination
          <select
            value={destination}
            onChange={(event) => {
              setDestination(event.target.value);
              clearResults();
            }}
          >
            <option value="">
              Select destination
            </option>

            {locations.map((location) => (
              <option
                key={location.id}
                value={location.id}
              >
                {location.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="bidholi-routing-actions">
        <button
          type="button"
          className="bidholi-find-route"
          disabled={loading}
          onClick={compareRoutes}
        >
          {loading
            ? "Comparing Routes..."
            : "Compare Routes"}
        </button>

        <button
          type="button"
          className="bidholi-clear-route"
          onClick={clearResults}
        >
          Clear Routes
        </button>
      </div>

      {error && (
        <p className="bidholi-routing-error" role="alert">
          {error}
        </p>
      )}

      {(shortestRoute || stairFreeRoute) && (
        <div className="cf-route-comparison">
          <div className="cf-comparison-heading">
            <h3>Available Walking Routes</h3>
            <p>
              Select a route to display it on the map.
            </p>
          </div>

          <div className="cf-comparison-grid">
            <RouteCard
              title="Shortest Route"
              type="shortest"
              route={shortestRoute}
              selected={
                selectedMode === "shortest"
              }
              onSelect={() =>
                selectRoute("shortest")
              }
              unavailable="Shortest route unavailable."
            />

            <RouteCard
              title="Stair-Free Route"
              type="stairfree"
              route={stairFreeRoute}
              selected={
                selectedMode === "stairfree"
              }
              onSelect={() =>
                selectRoute("stairfree")
              }
              unavailable={stairFreeError}
            />
          </div>

          {identicalRoutes && (
            <p className="cf-comparison-info">
              Both options use the same path.
              The shortest route already avoids stairs.
            </p>
          )}

          {!identicalRoutes &&
            distanceDifference !== null && (
              <p className="cf-comparison-info">
                Stair-free route adds approximately{" "}
                <strong>
                  {distanceDifference} metres
                </strong>{" "}
                compared with the shortest route.
              </p>
            )}

          {selectedRoute && (
            <div className="cf-active-route">
              <h3>Currently Selected Route</h3>

              <div className="bidholi-route-stats">
                <div>
                  <small>Estimated Distance</small>
                  <strong>
                    {selectedRoute.estimated_distance_m} m
                  </strong>
                </div>

                <div>
                  <small>Estimated Walking Time</small>
                  <strong>
                    {selectedRoute.estimated_time_min} min
                  </strong>
                </div>
              </div>

              <div className="cf-route-legend">
                <span>
                  <i className="cf-legend-start" />
                  Start
                </span>
                <span>
                  <i className="cf-legend-end" />
                  Destination
                </span>
                <span>
                  <i className="cf-legend-junction" />
                  Junction
                </span>
              </div>

              <p className="bidholi-route-path">
                {selectedRoute.path_names?.join(" → ")}
              </p>

              <p>
                {selectedRoute.contains_stairs
                  ? "This route includes stairs."
                  : "This route contains no mapped staircase edges."}
              </p>

              {selectedRoute.contains_provisional_edges && (
                <p className="bidholi-route-warning">
                  Some pedestrian connections require
                  further verification.
                </p>
              )}

              {selectedRoute.contains_unverified_geometry && (
                <p className="bidholi-route-warning">
                  Walking geometry has not been
                  verified on the ground.
                </p>
              )}

              <BidholiWalkingDirections
                route={selectedRoute}
              />
            </div>
          )}

          <p className="bidholi-route-disclaimer">
            Distances and times are estimates.
            Routes connect mapped GPS points and
            may not follow exact walking paths.
            Stair-free does not automatically mean
            wheelchair accessible.
          </p>
        </div>
      )}
    </section>
  );
}
