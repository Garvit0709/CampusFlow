
import { useEffect, useMemo, useState } from "react";

import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  CircleMarker,
  useMap,
} from "react-leaflet";

import L from "leaflet";

import "leaflet/dist/leaflet.css";
import "./BidholiMap.css";

import locations from "./data/bidholi_locations.json";

const CAMPUS_CENTER = [30.41717, 77.96819];

const categories = {
  all: "All Locations",
  academic: "Academic Blocks",
  food: "Cafes & Food",
  hostel: "Hostels",
  landmark: "Landmarks",
  sports: "Sports",
  museum: "Museum",
  service: "Services",
};

const colors = {
  academic: "#2563eb",
  food: "#ea580c",
  hostel: "#7c3aed",
  landmark: "#059669",
  sports: "#16a34a",
  museum: "#d97706",
  service: "#475569",
};

function createMarkerIcon(category) {
  const color = colors[category] || "#2563eb";

  return L.divIcon({
    className: "bidholi-marker",
    html: `
      <div
        style="
          background:${color};
          width:28px;
          height:28px;
          border-radius:50%;
          border:3px solid white;
          box-shadow:0 2px 8px #0005;
          display:flex;
          align-items:center;
          justify-content:center;
          color:white;
          font-size:16px;
        "
      >
        ●
      </div>
    `,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  });
}

function FlyToLocation({ location }) {
  const map = useMap();

  useEffect(() => {
    if (!location) return;

    map.flyTo(
      [location.latitude, location.longitude],
      19,
      { duration: 0.8 }
    );
  }, [location, map]);

  return null;
}

function BidholiMap({ onBack }) {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("all");
  const [selected, setSelected] = useState(null);

  const filteredLocations = useMemo(() => {
    return locations.filter((location) => {
      const matchesSearch = location.name
        .toLowerCase()
        .includes(search.toLowerCase().trim());

      const matchesCategory =
        category === "all" ||
        location.category === category;

      return matchesSearch && matchesCategory;
    });
  }, [search, category]);

  function selectLocation(location) {
    setSelected(location);
  }

  function handleBack() {
    if (onBack) {
      onBack();
    } else {
      window.location.href = "/";
    }
  }

  return (
    <div className="bidholi-page">
      <header className="bidholi-header">
        <div>
          <h1>CampusFlow</h1>
          <p>Explore UPES Bidholi - Energy Acres</p>
        </div>

        <button
          type="button"
          className="bidholi-back"
          onClick={handleBack}
        >
          Back to CampusFlow
        </button>
      </header>

      <div className="bidholi-layout">
        <aside className="bidholi-sidebar">
          <div className="bidholi-sidebar-heading">
            <h2>Campus Directory</h2>
            <p>{locations.length} mapped locations</p>
          </div>

          <input
            className="bidholi-search"
            type="search"
            placeholder="Search library, block, cafe..."
            value={search}
            onChange={(event) =>
              setSearch(event.target.value)
            }
            aria-label="Search campus locations"
          />

          <select
            className="bidholi-filter"
            value={category}
            onChange={(event) =>
              setCategory(event.target.value)
            }
            aria-label="Filter location category"
          >
            {Object.entries(categories).map(
              ([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              )
            )}
          </select>

          <div className="bidholi-location-list">
            {filteredLocations.length === 0 && (
              <p>No matching locations found.</p>
            )}

            {filteredLocations.map((location) => (
              <button
                key={location.id}
                className={
                  "bidholi-location-item " +
                  (selected?.id === location.id
                    ? "selected"
                    : "")
                }
                onClick={() =>
                  selectLocation(location)
                }
              >
                <span
                  className="bidholi-location-dot"
                  style={{
                    background:
                      colors[location.category] ||
                      "#2563eb",
                  }}
                />

                <span>
                  <strong>{location.name}</strong>
                  <small>
                    {categories[location.category] ||
                      "Campus Location"}
                  </small>
                </span>
              </button>
            ))}
          </div>
        </aside>

        <main className="bidholi-main">
          <div className="bidholi-map">
            <MapContainer
              center={CAMPUS_CENTER}
              zoom={18}
              zoomControl={true}
              style={{
                width: "100%",
                height: "100%",
              }}
            >
              <TileLayer
                attribution="&copy; OpenStreetMap contributors"
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                maxZoom={19}
              />

              <FlyToLocation location={selected} />

              {locations.map((location) => (
                <Marker
                  key={location.id}
                  position={[
                    location.latitude,
                    location.longitude,
                  ]}
                  icon={createMarkerIcon(
                    location.category
                  )}
                  eventHandlers={{
                    click: () =>
                      selectLocation(location),
                  }}
                >
                  <Popup>
                    <div className="bidholi-popup">
                      <h3>{location.name}</h3>

                      <p>
                        {categories[location.category] ||
                          "Campus Location"}
                      </p>

                      <p>
                        GPS: {location.latitude},{" "}
                        {location.longitude}
                      </p>

                      <p className="bidholi-unverified">
                        Entrance not yet verified
                      </p>

                      <button
                        onClick={() =>
                          selectLocation(location)
                        }
                      >
                        View Location
                      </button>
                    </div>
                  </Popup>
                </Marker>
              ))}

              {selected && (
                <CircleMarker
                  center={[
                    selected.latitude,
                    selected.longitude,
                  ]}
                  radius={19}
                  pathOptions={{
                    color: "#16a34a",
                    weight: 3,
                    fillOpacity: 0.1,
                  }}
                />
              )}
            </MapContainer>
          </div>

          {selected ? (
            <section className="bidholi-details">
              <div className="bidholi-photo">
                {selected.image_url ? (
                  <img
                    src={selected.image_url}
                    alt={selected.name}
                  />
                ) : (
                  <div className="bidholi-photo-empty">
                    <span>Photo coming soon</span>
                  </div>
                )}
              </div>

              <div className="bidholi-details-content">
                <h2>{selected.name}</h2>

                <p>
                  Category:{" "}
                  {categories[selected.category] ||
                    "Campus Location"}
                </p>

                <p>
                  Latitude: {selected.latitude}
                </p>

                <p>
                  Longitude: {selected.longitude}
                </p>

                <p className="bidholi-unverified">
                  GPS point recorded. Entrance and
                  walking access require verification.
                </p>

                <button
                  disabled
                  title="Walking routes are being mapped"
                >
                  Get Directions - Coming Soon
                </button>
              </div>
            </section>
          ) : (
            <section className="bidholi-empty-state">
              <h2>Discover UPES Bidholi</h2>
              <p>
                Select a building from the directory
                or click a marker on the map.
              </p>
            </section>
          )}

          <p className="bidholi-note">
            Locations are based on student-collected GPS
            coordinates. Walking paths and entrance
            positions have not yet been verified.
          </p>
        </main>
      </div>
    </div>
  );
}

export default BidholiMap;
