
import { useEffect, useState } from "react";
import {
  CircleMarker,
  Popup,
  useMapEvents,
} from "react-leaflet";

import "./BidholiJunctionEditor.css";

const STORAGE_KEY = "campusflow_bidholi_junctions_v1";

export const JUNCTIONS = [
  {
    id: "J1",
    name: "2nd–3rd Block Midway",
  },
  {
    id: "J2",
    name: "4th–5th Block Midway",
  },
  {
    id: "J3",
    name: "Café–Frisco Central Walkway",
  },
  {
    id: "J4",
    name: "3rd–6th Staircase Crossing",
  },
  {
    id: "J5",
    name: "5th Block to Gandhi Chowk Turn",
  },
  {
    id: "J6",
    name: "MAC–Library–IT Road Turn",
  },
  {
    id: "J7",
    name: "2nd–3rd Side Road to MAC",
  },
  {
    id: "J8",
    name: "Museum-side Road Junction",
  },
  {
    id: "J9",
    name: "MAC to Food Court 2 Turn",
  },
  {
    id: "J10",
    name: "Management Building–Girls Hostel Turn",
  },
];

const VALID_IDS = new Set(
  JUNCTIONS.map((junction) => junction.id)
);

function validCoordinate(value, limit) {
  return (
    typeof value === "number" &&
    Number.isFinite(value) &&
    Math.abs(value) <= limit
  );
}

function sanitizeJunctions(data) {
  if (!Array.isArray(data)) return [];

  const seen = new Set();

  return data.filter((item) => {
    if (!item || !VALID_IDS.has(item.id)) {
      return false;
    }

    if (seen.has(item.id)) return false;

    if (
      !validCoordinate(item.latitude, 90) ||
      !validCoordinate(item.longitude, 180)
    ) {
      return false;
    }

    seen.add(item.id);
    return true;
  }).map((item) => {
    const definition = JUNCTIONS.find(
      (junction) => junction.id === item.id
    );

    return {
      id: item.id,
      name: definition.name,
      latitude: item.latitude,
      longitude: item.longitude,
      type: "pedestrian_junction",
      position_source: "manual_map_click",
      verified_on_ground: false,
    };
  });
}

function loadSavedJunctions() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);

    return raw
      ? sanitizeJunctions(JSON.parse(raw))
      : [];
  } catch {
    return [];
  }
}

function downloadJSON(data) {
  const blob = new Blob(
    [JSON.stringify(data, null, 2)],
    { type: "application/json" }
  );

  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");

  link.href = url;
  link.download = "bidholi_junctions.json";

  document.body.appendChild(link);
  link.click();
  link.remove();

  URL.revokeObjectURL(url);
}

export function JunctionMapLayer({
  editing,
  selectedId,
  junctions,
  onPlace,
}) {
  useMapEvents({
    click(event) {
      if (!editing || !selectedId) return;

      onPlace(
        selectedId,
        event.latlng.lat,
        event.latlng.lng
      );
    },
  });

  return (
    <>
      {junctions.map((junction) => (
        <CircleMarker
          key={junction.id}
          center={[
            junction.latitude,
            junction.longitude,
          ]}
          radius={
            selectedId === junction.id ? 11 : 8
          }
          pathOptions={{
            color: "#92400e",
            fillColor:
              selectedId === junction.id
                ? "#16a34a"
                : "#f59e0b",
            fillOpacity: 0.95,
            weight: 3,
          }}
        >
          <Popup>
            <strong>
              {junction.id} — {junction.name}
            </strong>
            <p>
              Latitude: {junction.latitude.toFixed(7)}
            </p>
            <p>
              Longitude: {junction.longitude.toFixed(7)}
            </p>
            <p>
              Map-placed, not ground-verified.
            </p>
          </Popup>
        </CircleMarker>
      ))}
    </>
  );
}

export default function BidholiJunctionEditor({
  editing,
  setEditing,
  selectedId,
  setSelectedId,
  junctions,
  setJunctions,
}) {
  const [message, setMessage] = useState("");

  const savedCount = junctions.length;

  function removeJunction(id) {
    setJunctions((current) =>
      current.filter((item) => item.id !== id)
    );

    setMessage(`${id} removed.`);
  }

  function exportJunctions() {
    const output = {
      campus: "UPES Bidholi",
      schema_version: 1,
      coordinate_system: "WGS84",
      exported_at: new Date().toISOString(),
      junctions,
    };

    downloadJSON(output);
    setMessage("Junction JSON exported.");
  }

  async function importJunctions(event) {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      const parsed = JSON.parse(await file.text());

      if (
        parsed.campus !== "UPES Bidholi" ||
        parsed.schema_version !== 1 ||
        !Array.isArray(parsed.junctions)
      ) {
        throw new Error("Invalid junction file.");
      }

      const cleaned = sanitizeJunctions(
        parsed.junctions
      );

      if (
        cleaned.length !== parsed.junctions.length
      ) {
        throw new Error(
          "Some junction records are invalid."
        );
      }

      if (
        !window.confirm(
          "Replace current junctions with imported data?"
        )
      ) {
        return;
      }

      setJunctions(cleaned);
      setMessage("Junctions imported successfully.");
    } catch (error) {
      setMessage(error.message);
    } finally {
      event.target.value = "";
    }
  }

  function clearAll() {
    if (
      !window.confirm(
        "Delete all saved junction positions?"
      )
    ) {
      return;
    }

    setJunctions([]);
    setMessage("All junction positions cleared.");
  }

  return (
    <section className="junction-editor">
      <div className="junction-editor-header">
        <div>
          <span className="bidholi-eyebrow">
            PHASE 9.7.2
          </span>
          <h2>Pedestrian Junction Editor</h2>
          <p>
            Position road turns and pedestrian
            intersections on the campus map.
          </p>
        </div>

        <span className="junction-count">
          {savedCount} / {JUNCTIONS.length} placed
        </span>
      </div>

      <label className="junction-edit-toggle">
        <input
          type="checkbox"
          checked={editing}
          onChange={(event) =>
            setEditing(event.target.checked)
          }
        />
        Enable Junction Editing
      </label>

      {editing && (
        <p className="junction-instruction">
          Select a junction below, then click its
          position on the map. Clicking again will
          update that junction's coordinates.
        </p>
      )}

      <div className="junction-list">
        {JUNCTIONS.map((definition) => {
          const saved = junctions.find(
            (item) => item.id === definition.id
          );

          return (
            <div
              key={definition.id}
              className={
                "junction-item " +
                (selectedId === definition.id
                  ? "active"
                  : "")
              }
            >
              <div className="junction-item-info">
                <strong>{definition.id}</strong>
                <span>{definition.name}</span>
                <small>
                  {saved
                    ? `${saved.latitude.toFixed(6)}, ${saved.longitude.toFixed(6)}`
                    : "Not positioned"}
                </small>
              </div>

              <div className="junction-item-actions">
                <button
                  type="button"
                  disabled={!editing}
                  onClick={() =>
                    setSelectedId(definition.id)
                  }
                >
                  {saved ? "Move" : "Place"}
                </button>

                {saved && (
                  <button
                    type="button"
                    className="junction-remove"
                    onClick={() =>
                      removeJunction(definition.id)
                    }
                  >
                    Remove
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div className="junction-editor-actions">
        <button
          type="button"
          onClick={exportJunctions}
          disabled={savedCount === 0}
        >
          Export JSON
        </button>

        <label className="junction-import">
          Import JSON
          <input
            type="file"
            accept=".json,application/json"
            onChange={importJunctions}
          />
        </label>

        <button
          type="button"
          className="junction-clear"
          onClick={clearAll}
          disabled={savedCount === 0}
        >
          Clear All
        </button>
      </div>

      {message && (
        <p className="junction-message" role="status">
          {message}
        </p>
      )}

      <p className="junction-note">
        Positions are saved in this browser only.
        Export JSON regularly. These points are not
        yet connected to PostgreSQL or Dijkstra.
      </p>
    </section>
  );
}

export function useBidholiJunctions() {
  const [junctions, setJunctions] = useState(
    loadSavedJunctions
  );

  useEffect(() => {
    try {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify(junctions)
      );
    } catch (error) {
      console.error(
        "Unable to save junctions:",
        error
      );
    }
  }, [junctions]);

  return [junctions, setJunctions];
}
