import BidholiMobileToolbar from "./BidholiMobileToolbar";
import { useEffect, useMemo, useState } from "react";
import BidholiJunctionEditor, {
  JUNCTIONS,
  JunctionMapLayer,
  useBidholiJunctions,
} from "./BidholiJunctionEditor";

import { LayersControl } from "react-leaflet";

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

import {
  getLocationPhotos,
  getLocationDetails,
} from "./data/bidholiPhotos";

import BidholiRoutingPanel, {
  BidholiRouteLine,
} from "./BidholiRoutingPanel";

const CAMPUS_CENTER = [30.41717, 77.96819];

const CATEGORY_INFO = {
  academic: {
    label: "Academic",
    icon: "🎓",
    color: "#2563eb",
  },
  food: {
    label: "Food & Cafes",
    icon: "☕",
    color: "#ea580c",
  },
  hostel: {
    label: "Hostels",
    icon: "🏠",
    color: "#7c3aed",
  },
  landmark: {
    label: "Landmarks",
    icon: "📍",
    color: "#059669",
  },
  sports: {
    label: "Sports",
    icon: "⚽",
    color: "#16a34a",
  },
  museum: {
    label: "Museum",
    icon: "🏛️",
    color: "#d97706",
  },
  service: {
    label: "Services",
    icon: "🏢",
    color: "#475569",
  },
};

const DEFAULT_CATEGORY = {
  label: "Campus Location",
  icon: "📍",
  color: "#2563eb",
};

function getCategory(category) {
  return CATEGORY_INFO[category] || DEFAULT_CATEGORY;
}

// Cache Leaflet icons to avoid recreating them
// on every component render.
const markerCache = {};

function getMarkerIcon(category) {
  const key = category || "default";

  if (markerCache[key]) {
    return markerCache[key];
  }

  const info = getCategory(category);

  const icon = L.divIcon({
    className: "bidholi-custom-marker",
    html: `
      <div
        class="bidholi-pin"
        style="--pin-color:${info.color}"
      >
        <span>${info.icon}</span>
      </div>
    `,
    iconSize: [42, 46],
    iconAnchor: [21, 43],
    popupAnchor: [0, -40],
  });

  markerCache[key] = icon;

  return icon;
}

// Move the map when a building is selected.
function ResizeMapOnLayoutChange() {
  const map = useMap();

  useEffect(() => {
    const container = map.getContainer();
    const resizeObserver = typeof ResizeObserver !== "undefined"
      ? new ResizeObserver(() => map.invalidateSize())
      : null;
    resizeObserver?.observe(container);
    map.invalidateSize();
    return () => resizeObserver?.disconnect();
  }, [map]);

  return null;
}

function FlyToLocation({ location }) {
  const map = useMap();

  useEffect(() => {
    if (!location) return;

    map.flyTo(
      [
        Number(location.latitude),
        Number(location.longitude),
      ],
      19,
      {
        duration: 0.8,
      }
    );
  }, [location, map]);

  return null;
}

// Display a photo, or a placeholder if
// the photo has not been added yet.
function LocationPhoto({
  src,
  alt,
  className = "",
}) {
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    setFailed(false);
  }, [src]);

  if (!src || failed) {
    return (
      <div
        className={
          `bidholi-image-fallback ${className}`
        }
      >
        <span className="fallback-icon">
          📷
        </span>

        <span>Photo coming soon</span>
      </div>
    );
  }

  return (
    <img
      className={className}
      src={src}
      alt={alt}
      loading="lazy"
      onError={() => setFailed(true)}
    />
  );
}

// ============================================================
// MAIN BIDHOLI MAP COMPONENT
// ============================================================

function BidholiMap({ onBack }) {
  // Location search and selection
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("all");
  const [selected, setSelected] = useState(null);

  // Photo gallery
  const [photoIndex, setPhotoIndex] = useState(0);

  // Phase 9.6: Dijkstra route state
  const [bidholiRoute, setBidholiRoute] = useState(null);

  const [junctions, setJunctions] = useBidholiJunctions();
  const [junctionEditing, setJunctionEditing] = useState(false);
  const [selectedJunctionId, setSelectedJunctionId] = useState("J1");

  function placeJunction(id, latitude, longitude) {
    const definition = JUNCTIONS.find((item) => item.id === id);
    if (!definition) return;
    setJunctions((current) => [
      ...current.filter((item) => item.id !== id),
      {
        id,
        name: definition.name,
        latitude,
        longitude,
        type: "pedestrian_junction",
        position_source: "manual_map_click",
        verified_on_ground: false,
      },
    ]);
  }


  // Validate the imported GPS locations.
  const validLocations = useMemo(() => {
    return locations.filter((location) => {
      const latitude = Number(location.latitude);
      const longitude = Number(location.longitude);

      return (
        Number.isFinite(latitude) &&
        Number.isFinite(longitude) &&
        latitude >= -90 &&
        latitude <= 90 &&
        longitude >= -180 &&
        longitude <= 180
      );
    });
  }, []);

  // Filter the location directory.
  const filteredLocations = useMemo(() => {
    const query = search.trim().toLowerCase();

    return validLocations.filter((location) => {
      const name = String(
        location.name || ""
      ).toLowerCase();

      const matchesSearch = name.includes(query);

      const matchesCategory =
        category === "all" ||
        location.category === category;

      return matchesSearch && matchesCategory;
    });
  }, [search, category, validLocations]);

  // Photos for the currently selected location.
  const photos = useMemo(() => {
    return selected
      ? getLocationPhotos(selected)
      : [];
  }, [selected]);

  // Description and facilities.
  const details = useMemo(() => {
    return selected
      ? getLocationDetails(selected)
      : null;
  }, [selected]);

  function selectLocation(location) {
    setSelected(location);
    setPhotoIndex(0);
  }

  function handleBack() {
    if (typeof onBack === "function") {
      onBack();
    } else {
      window.location.href = "/";
    }
  }

  function nextPhoto() {
    if (photos.length < 2) return;

    setPhotoIndex((index) => {
      return (index + 1) % photos.length;
    });
  }

  function previousPhoto() {
    if (photos.length < 2) return;

    setPhotoIndex((index) => {
      return (
        index - 1 + photos.length
      ) % photos.length;
    });
  }

  const currentPhoto =
    photos[photoIndex] || null;

  // ==========================================================
  // RENDER
  // ==========================================================

  return (
    <div className="bidholi-page">
      {/* HEADER */}
      <header className="bidholi-header">
        <div className="bidholi-brand">
          <div className="bidholi-brand-icon">
            CF
          </div>

          <div>
            <h1>CampusFlow</h1>
            <p>
              UPES Bidholi - Energy Acres
            </p>
          </div>
        </div>

        <button
          className="bidholi-back"
          type="button"
          onClick={handleBack}
        >
          ← Back to CampusFlow
        </button>
      </header>

      <div className="bidholi-layout">
        {/* SIDEBAR */}
        <aside
  id="bidholi-mobile-directory"
  className="bidholi-sidebar"
>
          <div className="bidholi-sidebar-heading">
            <span className="bidholi-eyebrow">
              EXPLORE CAMPUS
            </span>

            <h2>Campus Directory</h2>

            <p>
              {validLocations.length} mapped locations
            </p>
          </div>

          {/* SEARCH */}
          <div className="bidholi-search-box">
            <span>⌕</span>

            <input
              type="search"
              placeholder="Search buildings, cafes..."
              aria-label="Search locations"
              value={search}
              onChange={(event) => {
                setSearch(event.target.value);
              }}
            />
          </div>

          {/* CATEGORY FILTER */}
          <select
            className="bidholi-filter"
            aria-label="Filter category"
            value={category}
            onChange={(event) => {
              setCategory(event.target.value);
            }}
          >
            <option value="all">
              All Categories
            </option>

            {Object.entries(CATEGORY_INFO).map(
              ([key, info]) => (
                <option key={key} value={key}>
                  {info.label}
                </option>
              )
            )}
          </select>

          {/* LOCATION DIRECTORY */}
          <div className="bidholi-location-list">
            {filteredLocations.length === 0 && (
              <p className="bidholi-no-results">
                No matching locations found.
              </p>
            )}

            {filteredLocations.map((location) => {
              const info = getCategory(
                location.category
              );

              return (
                <button
                  type="button"
                  key={location.id}
                  className={
                    "bidholi-location-item " +
                    (selected?.id === location.id
                      ? "selected"
                      : "")
                  }
                  onClick={() => {
                    selectLocation(location);
                  }}
                >
                  <span
                    className="bidholi-list-icon"
                    style={{
                      background: `${info.color}16`,
                      color: info.color,
                    }}
                  >
                    {info.icon}
                  </span>

                  <span className="bidholi-list-text">
                    <strong>
                      {location.name}
                    </strong>

                    <small>
                      {info.label}
                    </small>
                  </span>

                  <span className="bidholi-list-arrow">
                    ›
                  </span>
                </button>
              );
            })}
          </div>
        </aside>

        {/* MAIN CONTENT */}
        <main className="bidholi-main">
          {/* ROUTING PANEL */}
          <section id="bidholi-mobile-routes">
  <BidholiRoutingPanel
    locations={validLocations}
    onRoute={setBidholiRoute}
  />
</section>

          <section id="bidholi-mobile-editor">
  <BidholiJunctionEditor
    editing={junctionEditing}
    setEditing={setJunctionEditing}
    selectedId={selectedJunctionId}
    setSelectedId={setSelectedJunctionId}
    junctions={junctions}
    setJunctions={setJunctions}
  />
</section>

          {/* MAP TOOLBAR */}
          <div className="bidholi-map-toolbar">
            <div>
              <strong>
                UPES Bidholi Map
              </strong>

              <span>
                Select a building or calculate a route
              </span>
            </div>

            <span className="bidholi-count">
              {validLocations.length} Places
            </span>
          </div>

          {/* LEAFLET MAP */}
          <div id="bidholi-mobile-map" className={`bidholi-map${junctionEditing ? " junction-editing" : ""}`}>
            <MapContainer
              center={CAMPUS_CENTER}
              zoom={18}
              zoomControl
              style={{
                width: "100%",
                height: "100%",
              }}
            >
              <ResizeMapOnLayoutChange />
              <LayersControl position="topright">
                <LayersControl.BaseLayer checked name="OpenStreetMap">
                  <TileLayer
                    attribution="&copy; OpenStreetMap contributors"
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    maxZoom={19}
                  />
                </LayersControl.BaseLayer>
                <LayersControl.BaseLayer name="Satellite Imagery">
                  <TileLayer
                    attribution="Tiles &copy; Esri and imagery providers"
                    url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                    maxZoom={19}
                  />
                </LayersControl.BaseLayer>
              </LayersControl>

              <JunctionMapLayer
                editing={junctionEditing}
                selectedId={selectedJunctionId}
                junctions={junctions}
                onPlace={placeJunction}
              />

              {/* PHASE 9.6 ROUTE LINE */}
              <BidholiRouteLine
                route={bidholiRoute}
              />

              {/* LOCATION FOCUS */}
              <FlyToLocation
                location={selected}
              />

              {/* LOCATION MARKERS */}
              {validLocations.map((location) => {
                const info = getCategory(
                  location.category
                );

                const locationPhotos =
                  getLocationPhotos(location);

                return (
                  <Marker
                    key={location.id}
                    position={[
                      Number(location.latitude),
                      Number(location.longitude),
                    ]}
                    icon={getMarkerIcon(
                      location.category
                    )}
                    eventHandlers={{
                      click: () => {
                        selectLocation(location);
                      },
                    }}
                  >
                    <Popup>
                      <div className="bidholi-popup">
                        <LocationPhoto
                          src={
                            locationPhotos[0]?.src ||
                            location.image_url
                          }
                          alt={location.name}
                          className="bidholi-popup-image"
                        />

                        <div className="bidholi-popup-body">
                          <span
                            className="bidholi-popup-category"
                            style={{
                              color: info.color,
                            }}
                          >
                            {info.icon} {info.label}
                          </span>

                          <h3>
                            {location.name}
                          </h3>

                          <p>
                            UPES Bidholi Campus
                          </p>

                          <button
                            type="button"
                            onClick={() => {
                              selectLocation(location);
                            }}
                          >
                            View Details
                          </button>
                        </div>
                      </div>
                    </Popup>
                  </Marker>
                );
              })}

              {/* SELECTED LOCATION HIGHLIGHT */}
              {selected && (
                <CircleMarker
                  center={[
                    Number(selected.latitude),
                    Number(selected.longitude),
                  ]}
                  radius={20}
                  pathOptions={{
                    color: "#16a34a",
                    weight: 3,
                    fillOpacity: 0.08,
                  }}
                />
              )}
            </MapContainer>
          </div>

          {/* LOCATION DETAILS */}
          {selected ? (
            <section className="bidholi-details">
              {/* PHOTO GALLERY */}
              <div className="bidholi-gallery">
                <LocationPhoto
                  src={
                    currentPhoto?.src ||
                    selected.image_url
                  }
                  alt={selected.name}
                  className="bidholi-gallery-image"
                />

                {photos.length > 1 && (
                  <div className="bidholi-gallery-controls">
                    <button
                      type="button"
                      onClick={previousPhoto}
                    >
                      ← Previous
                    </button>

                    <span>
                      {photoIndex + 1} / {photos.length}
                    </span>

                    <button
                      type="button"
                      onClick={nextPhoto}
                    >
                      Next →
                    </button>
                  </div>
                )}
              </div>

              {/* BUILDING INFORMATION */}
              <div className="bidholi-details-content">
                <span className="bidholi-eyebrow">
                  LOCATION DETAILS
                </span>

                <h2>
                  {selected.name}
                </h2>

                <span className="bidholi-category-badge">
                  {getCategory(
                    selected.category
                  ).icon}{" "}
                  {getCategory(
                    selected.category
                  ).label}
                </span>

                <p className="bidholi-description">
                  {details.description}
                </p>

                {details.facilities.length > 0 && (
                  <div className="bidholi-facilities">
                    {details.facilities.map(
                      (facility) => (
                        <span key={facility}>
                          {facility}
                        </span>
                      )
                    )}
                  </div>
                )}

                {/* GPS COORDINATES */}
                <div className="bidholi-coordinates">
                  <div>
                    <small>
                      Latitude
                    </small>

                    <strong>
                      {selected.latitude}
                    </strong>
                  </div>

                  <div>
                    <small>
                      Longitude
                    </small>

                    <strong>
                      {selected.longitude}
                    </strong>
                  </div>
                </div>

                <p className="bidholi-verification">
                  Student-recorded GPS point.
                  Building entrances and pedestrian
                  routes still require verification.
                </p>

                <button
                  type="button"
                  className="bidholi-directions-button"
                  disabled
                  title="Select a route using the routing panel above"
                >
                  Use Find Route Above
                </button>
              </div>
            </section>
          ) : (
            /* NO LOCATION SELECTED */
            <section className="bidholi-empty-state">
              <span>📍</span>

              <div>
                <h2>
                  Discover UPES Bidholi
                </h2>

                <p>
                  Search the campus directory,
                  select a building, or use the
                  routing panel to calculate an
                  estimated walking route.
                </p>
              </div>
            </section>
          )}

          {/* MAP DISCLAIMER */}
          <p className="bidholi-note">
            CampusFlow uses student-collected GPS
            coordinates and estimated walking
            distances. Highlighted routes connect
            mapped locations and may not follow
            actual pedestrian walkways.
          </p>
        </main>
      </div>
      <BidholiMobileToolbar />
    </div>
  );
}

export default BidholiMap;
