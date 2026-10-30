
import { useCallback, useEffect, useState } from "react";

import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
  useMap,
} from "react-leaflet";

import AuthPage from "./AuthPage";
import AdminDashboard from "./AdminDashboard";

import "leaflet/dist/leaflet.css";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

const DEFAULT_DATE = "2026-10-26";
const DEFAULT_HOUR = "13:00";

const HOURS = Array.from({ length: 14 }, (_, i) =>
  `${String(i + 7).padStart(2, "0")}:00`
);

function MapUpdater({ center }) {
  const map = useMap();

  useEffect(() => {
    map.setView(center, 16);
  }, [center, map]);

  return null;
}

async function parseResponse(response) {
  if (!response.ok) {
    let message = "Request failed";

    try {
      const data = await response.json();
      if (typeof data.detail === "string") {
        message = data.detail;
      }
    } catch {
      // Keep default message
    }

    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  return response.json();
}

function App() {
  // Authentication
  const [session, setSession] = useState(null);
  const [showAdmin, setShowAdmin] = useState(false);

  const user = session?.user;
  const token = session?.token;

  const isAdmin = user?.role === "admin";

  const handleLogout = useCallback(() => {
    setSession(null);
    setShowAdmin(false);
  }, []);

  // Campus data
  const [campusLocations, setCampusLocations] = useState([]);
  const [campusEdges, setCampusEdges] = useState([]);
  const [dataLoading, setDataLoading] = useState(true);
  const [dataError, setDataError] = useState("");

  // Routing
  const [source, setSource] = useState("");
  const [destination, setDestination] = useState("");
  const [routingMode, setRoutingMode] = useState("smart");
  const [routeDate, setRouteDate] = useState(DEFAULT_DATE);
  const [routeHour, setRouteHour] = useState(DEFAULT_HOUR);
  const [route, setRoute] = useState(null);
  const [routeMessage, setRouteMessage] = useState("");
  const [loadingRoute, setLoadingRoute] = useState(false);

  // Crowd reporting
  const [crowdLocation, setCrowdLocation] = useState("");
  const [crowdLevel, setCrowdLevel] = useState("medium");
  const [crowdMessage, setCrowdMessage] = useState("");
  const [crowdError, setCrowdError] = useState(false);
  const [submittingCrowd, setSubmittingCrowd] = useState(false);
  const [crowdReports, setCrowdReports] = useState([]);
  const [currentCrowds, setCurrentCrowds] = useState({});

  // ML prediction
  const [predictionLocation, setPredictionLocation] =
    useState("cafeteria");
  const [predictionDate, setPredictionDate] =
    useState(DEFAULT_DATE);
  const [predictionHour, setPredictionHour] =
    useState(DEFAULT_HOUR);
  const [prediction, setPrediction] = useState(null);
  const [predictionError, setPredictionError] = useState("");
  const [predicting, setPredicting] = useState(false);

  // Load public campus data
  useEffect(() => {
    let active = true;

    async function loadData() {
      try {
        const responses = await Promise.all([
          fetch(`${API_URL}/locations`),
          fetch(`${API_URL}/edges`),
          fetch(`${API_URL}/crowd/current`),
          fetch(`${API_URL}/crowd/reports`),
        ]);

        const [locations, edges, crowds, reports] =
          await Promise.all(
            responses.map(parseResponse)
          );

        if (!active) return;

        setCampusLocations(locations);
        setCampusEdges(edges);
        setCurrentCrowds(crowds);
        setCrowdReports(reports);
        setDataError("");
      } catch (error) {
        if (active) {
          setDataError(
            "Unable to load campus data. Check FastAPI and PostgreSQL."
          );
          console.error(error);
        }
      } finally {
        if (active) setDataLoading(false);
      }
    }

    loadData();

    return () => {
      active = false;
    };
  }, []);

  async function refreshCrowdData() {
    const responses = await Promise.all([
      fetch(`${API_URL}/crowd/current`),
      fetch(`${API_URL}/crowd/reports`),
    ]);

    const [crowds, reports] = await Promise.all(
      responses.map(parseResponse)
    );

    setCurrentCrowds(crowds);
    setCrowdReports(reports);
  }

  function getLocation(id) {
    return campusLocations.find((loc) => loc.id === id);
  }

  function resetRoute() {
    setRoute(null);
    setRouteMessage("");
  }

  // Shortest, live smart and ML routing
  async function findRoute() {
    if (!source || !destination) {
      setRouteMessage("Please select both locations.");
      setRoute(null);
      return;
    }

    if (source === destination) {
      setRouteMessage("Please select different locations.");
      setRoute(null);
      return;
    }

    if (routingMode === "ml" && !routeDate) {
      setRouteMessage("Select a departure date.");
      return;
    }

    setLoadingRoute(true);
    resetRoute();

    const payload = {
      source,
      destination,
      mode: routingMode,
    };

    if (routingMode === "ml") {
      payload.departure_time =
        `${routeDate}T${routeHour}:00`;
    }

    try {
      const response = await fetch(
        `${API_URL}/routes/recommend`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        }
      );

      setRoute(await parseResponse(response));
    } catch (error) {
      setRouteMessage(error.message);
    } finally {
      setLoadingRoute(false);
    }
  }

  // Authenticated crowd reporting
  async function submitCrowdReport() {
    if (!token) {
      setCrowdError(true);
      setCrowdMessage("Please log in first.");
      return;
    }

    if (!crowdLocation) {
      setCrowdError(true);
      setCrowdMessage("Please select a location.");
      return;
    }

    setSubmittingCrowd(true);
    setCrowdError(false);
    setCrowdMessage("");

    try {
      const response = await fetch(
        `${API_URL}/crowd/report`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            location_id: crowdLocation,
            crowd_level: crowdLevel,
          }),
        }
      );

      await parseResponse(response);

      setCrowdMessage(
        "Crowd report submitted successfully!"
      );

      setCrowdLocation("");
      setCrowdLevel("medium");
      resetRoute();

      try {
        await refreshCrowdData();
      } catch {
        setCrowdMessage(
          "Report saved, but crowd data could not refresh."
        );
      }
    } catch (error) {
      if (error.status === 401) {
        handleLogout();
        return;
      }

      setCrowdError(true);
      setCrowdMessage(error.message);
    } finally {
      setSubmittingCrowd(false);
    }
  }

  // Single-location ML prediction
  async function predictCrowd() {
    if (!predictionLocation || !predictionDate) {
      setPredictionError("Select location and date.");
      return;
    }

    setPredicting(true);
    setPrediction(null);
    setPredictionError("");

    try {
      const response = await fetch(
        `${API_URL}/crowd/predict`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            location_id: predictionLocation,
            prediction_time:
              `${predictionDate}T${predictionHour}:00`,
          }),
        }
      );

      setPrediction(await parseResponse(response));
    } catch (error) {
      setPredictionError(error.message);
    } finally {
      setPredicting(false);
    }
  }

  const routeCoordinates = route
    ? route.path
        .map((id) => getLocation(id))
        .filter(Boolean)
        .map((loc) => loc.position)
    : [];

  const routeNames = route
    ? route.path
        .map((id) => getLocation(id)?.name || id)
        .join(" → ")
    : "";

  const campusCenter = campusLocations.length
    ? campusLocations[0].position
    : [28.6144, 77.2105];

  const predictionPercentages = prediction
    ? ["low", "medium", "high"].map((level) => ({
        level,
        percentage:
          (prediction.probabilities?.[level] || 0) * 100,
      }))
    : [];

  // Authentication screen
  if (!session) {
    return <AuthPage onLogin={setSession} />;
  }

  // Protected admin dashboard
  if (showAdmin && isAdmin) {
    return (
      <AdminDashboard
        token={token}
        onBack={() => setShowAdmin(false)}
        onLogout={handleLogout}
      />
    );
  }

  return (
    <div className="app">
      <header className="header">
        <h1>CampusFlow</h1>

        <p>
          Intelligent Campus Navigation & Crowd Prediction
        </p>

        <div className="app-user-bar">
          <span>
            Welcome, {user.full_name}
            {" "}({user.role})
          </span>

          {isAdmin && (
            <button
              className="admin-open-button"
              onClick={() => setShowAdmin(true)}
            >
              Open Admin Dashboard
            </button>
          )}

          <button
            className="logout-button"
            onClick={handleLogout}
          >
            Logout
          </button>
        </div>
      </header>

      <main>
        {dataLoading && (
          <p className="message">
            Loading campus data...
          </p>
        )}

        {dataError && (
          <p className="message" role="alert">
            {dataError}
          </p>
        )}

        {/* ROUTING */}
        <section className="controls">
          <select
            value={source}
            aria-label="Starting point"
            onChange={(e) => {
              setSource(e.target.value);
              resetRoute();
            }}
          >
            <option value="">Select Starting Point</option>
            {campusLocations.map((loc) => (
              <option key={loc.id} value={loc.id}>
                {loc.name}
              </option>
            ))}
          </select>

          <select
            value={destination}
            aria-label="Destination"
            onChange={(e) => {
              setDestination(e.target.value);
              resetRoute();
            }}
          >
            <option value="">Select Destination</option>
            {campusLocations.map((loc) => (
              <option key={loc.id} value={loc.id}>
                {loc.name}
              </option>
            ))}
          </select>

          <select
            value={routingMode}
            aria-label="Routing mode"
            onChange={(e) => {
              setRoutingMode(e.target.value);
              resetRoute();
            }}
          >
            <option value="shortest">
              Shortest Distance
            </option>
            <option value="smart">
              Smart Route (Live Reports)
            </option>
            <option value="ml">
              AI Predicted Smart Route
            </option>
          </select>

          {routingMode === "ml" && (
            <>
              <input
                type="date"
                aria-label="Departure date"
                value={routeDate}
                onChange={(e) => {
                  setRouteDate(e.target.value);
                  resetRoute();
                }}
              />

              <select
                aria-label="Departure hour"
                value={routeHour}
                onChange={(e) => {
                  setRouteHour(e.target.value);
                  resetRoute();
                }}
              >
                {HOURS.map((hour) => (
                  <option key={hour} value={hour}>
                    {hour}
                  </option>
                ))}
              </select>
            </>
          )}

          <button
            onClick={findRoute}
            disabled={
              loadingRoute ||
              dataLoading ||
              !!dataError
            }
          >
            {loadingRoute
              ? "Calculating..."
              : "Find Route"}
          </button>
        </section>

        {routeMessage && (
          <p className="message" role="status">
            {routeMessage}
          </p>
        )}

        {route && (
          <section className="route-info">
            <h2>
              {route.mode === "ml"
                ? "AI Predicted Smart Route"
                : route.mode === "smart"
                  ? "Smart Recommended Route"
                  : "Shortest Distance Route"}
            </h2>

            <p>
              <strong>Distance:</strong>{" "}
              {route.distance} meters
            </p>

            <p>
              <strong>Estimated Walking Time:</strong>{" "}
              {route.estimated_time} minutes
            </p>

            <p>
              <strong>Route Crowd Level:</strong>{" "}
              {route.crowd_level.toUpperCase()}
            </p>

            <p>
              <strong>Path:</strong> {routeNames}
            </p>

            <p>
              <strong>Congestion Source:</strong>{" "}
              {route.crowd_source === "ml_prediction"
                ? "Random Forest ML Prediction"
                : route.crowd_source === "live_reports"
                  ? "Recent Student Reports"
                  : "Distance Only"}
            </p>

            {route.mode === "ml" && (
              <p>
                <strong>Departure:</strong>{" "}
                {route.departure_time?.replace("T", " ")}
              </p>
            )}
          </section>
        )}

        {/* CROWD REPORTING */}
        <section className="crowd-section">
          <h2>Report Campus Crowd</h2>
          <p>
            Help students identify congested areas.
          </p>

          <div className="crowd-controls">
            <select
              value={crowdLocation}
              onChange={(e) =>
                setCrowdLocation(e.target.value)
              }
            >
              <option value="">Select Location</option>

              {campusLocations.map((loc) => (
                <option key={loc.id} value={loc.id}>
                  {loc.name}
                </option>
              ))}
            </select>

            <select
              value={crowdLevel}
              onChange={(e) =>
                setCrowdLevel(e.target.value)
              }
            >
              <option value="low">Low Crowd</option>
              <option value="medium">Medium Crowd</option>
              <option value="high">High Crowd</option>
            </select>

            <button
              onClick={submitCrowdReport}
              disabled={
                submittingCrowd ||
                dataLoading ||
                !!dataError
              }
            >
              {submittingCrowd
                ? "Submitting..."
                : "Submit Crowd Report"}
            </button>
          </div>

          {crowdMessage && (
            <p
              className={
                crowdError
                  ? "crowd-message error"
                  : "crowd-message"
              }
              role="status"
            >
              {crowdMessage}
            </p>
          )}
        </section>

        {/* AI PREDICTION */}
        <section className="prediction-section">
          <div className="prediction-heading">
            <div>
              <h2>AI Crowd Prediction</h2>
              <p>
                Predict congestion at a campus location.
              </p>
            </div>

            <span className="ai-label">
              AI Powered
            </span>
          </div>

          <div className="prediction-controls">
            <div className="prediction-field">
              <label htmlFor="prediction-location">
                Campus Location
              </label>

              <select
                id="prediction-location"
                value={predictionLocation}
                onChange={(e) => {
                  setPredictionLocation(e.target.value);
                  setPrediction(null);
                }}
              >
                {campusLocations.map((loc) => (
                  <option key={loc.id} value={loc.id}>
                    {loc.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="prediction-field">
              <label htmlFor="prediction-date">
                Prediction Date
              </label>

              <input
                id="prediction-date"
                type="date"
                value={predictionDate}
                onChange={(e) => {
                  setPredictionDate(e.target.value);
                  setPrediction(null);
                }}
              />
            </div>

            <div className="prediction-field">
              <label htmlFor="prediction-hour">
                Prediction Time
              </label>

              <select
                id="prediction-hour"
                value={predictionHour}
                onChange={(e) => {
                  setPredictionHour(e.target.value);
                  setPrediction(null);
                }}
              >
                {HOURS.map((hour) => (
                  <option key={hour} value={hour}>
                    {hour}
                  </option>
                ))}
              </select>
            </div>

            <button
              className="predict-button"
              onClick={predictCrowd}
              disabled={
                predicting ||
                dataLoading ||
                !!dataError
              }
            >
              {predicting
                ? "Predicting..."
                : "Predict Crowd"}
            </button>
          </div>

          {predictionError && (
            <p
              className="prediction-error"
              role="alert"
            >
              {predictionError}
            </p>
          )}

          {prediction && (
            <div className="prediction-result">
              <div className="prediction-result-header">
                <div>
                  <p className="result-label">
                    Predicted Crowd Level
                  </p>

                  <h3>
                    {getLocation(prediction.location_id)?.name ||
                      prediction.location_id}
                  </h3>

                  <p className="prediction-time">
                    {prediction.prediction_time.replace(
                      "T", " "
                    )}
                  </p>
                </div>

                <span
                  className={
                    `prediction-badge ` +
                    prediction.predicted_crowd
                  }
                >
                  {prediction.predicted_crowd.toUpperCase()}
                </span>
              </div>

              <div className="confidence-box">
                <span>Model Confidence</span>

                <strong>
                  {Number(prediction.confidence).toFixed(2)}%
                </strong>
              </div>

              <h4>Predicted Class Probabilities</h4>

              <div className="probability-list">
                {predictionPercentages.map((item) => (
                  <div
                    className="probability-item"
                    key={item.level}
                  >
                    <div className="probability-label">
                      <span>
                        {item.level.toUpperCase()}
                      </span>
                      <strong>
                        {item.percentage.toFixed(2)}%
                      </strong>
                    </div>

                    <div className="probability-track">
                      <div
                        className={
                          `probability-fill ${item.level}`
                        }
                        style={{
                          width: `${item.percentage}%`,
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>

              <p className="prediction-disclaimer">
                Model trained on synthetic campus data.
                Predictions are demonstration estimates.
              </p>
            </div>
          )}
        </section>

        {/* RECENT CROWD REPORTS */}
        <section className="reports-section">
          <h2>Recent Crowd Reports</h2>

          {crowdReports.length === 0 ? (
            <p>No crowd reports available.</p>
          ) : (
            <div className="reports-list">
              {crowdReports.slice(0, 8).map((report) => (
                <div
                  className="report-item"
                  key={report.id}
                >
                  <span>
                    {report.location_name}
                  </span>

                  <span
                    className={
                      `crowd-badge ${report.crowd_level}`
                    }
                  >
                    {report.crowd_level.toUpperCase()}
                  </span>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* INTERACTIVE CAMPUS MAP */}
        <div className="map-wrapper">
          <MapContainer
            center={campusCenter}
            zoom={16}
            style={{
              height: "100%",
              width: "100%",
            }}
          >
            <MapUpdater center={campusCenter} />

            <TileLayer
              attribution="&copy; OpenStreetMap contributors"
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />

            {campusLocations.map((loc) => (
              <Marker
                key={loc.id}
                position={loc.position}
              >
                <Popup>
                  <strong>{loc.name}</strong>
                  <p>
                    Recent Crowd:{" "}
                    {(
                      currentCrowds[loc.id] || "low"
                    ).toUpperCase()}
                  </p>
                </Popup>
              </Marker>
            ))}

            {campusEdges.map((edge, index) => {
              const from = getLocation(edge.from);
              const to = getLocation(edge.to);

              if (!from || !to) return null;

              return (
                <Polyline
                  key={index}
                  positions={[
                    from.position,
                    to.position,
                  ]}
                  pathOptions={{
                    color: "#94a3b8",
                    weight: 3,
                    opacity: 0.65,
                  }}
                />
              );
            })}

            {routeCoordinates.length > 1 && (
              <Polyline
                positions={routeCoordinates}
                pathOptions={{
                  color:
                    route.mode === "ml"
                      ? "#7c3aed"
                      : route.mode === "smart"
                        ? "#16a34a"
                        : "#2563eb",
                  weight: 7,
                  opacity: 0.9,
                }}
              />
            )}
          </MapContainer>
        </div>
      </main>
    </div>
  );
}

export default App;
