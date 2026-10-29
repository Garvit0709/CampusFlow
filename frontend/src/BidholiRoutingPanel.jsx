import { useState } from "react";
import { Polyline } from "react-leaflet";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export function BidholiRouteLine({ route }) {
  if (!route?.coordinates || route.coordinates.length < 2) return null;
  return <Polyline positions={route.coordinates} pathOptions={{ color: "#7c3aed", weight: 6, opacity: 0.85 }} />;
}

export default function BidholiRoutingPanel({ locations, onRoute }) {
  const [source, setSource] = useState("");
  const [destination, setDestination] = useState("");
  const [avoidStairs, setAvoidStairs] = useState(false);
  const [route, setRoute] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function findRoute(event) {
    event.preventDefault();
    setError(""); setRoute(null); onRoute(null);
    if (!source || !destination || source === destination) {
      setError("Select two different locations."); return;
    }
    setLoading(true);
    try {
      const response = await fetch(`${API}/bidholi/route`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source, destination, avoid_stairs: avoidStairs }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Unable to calculate route");
      setRoute(data); onRoute(data);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }

  return (
    <section className="bidholi-route-panel" style={{padding:16, background:"white", borderBottom:"1px solid #ddd"}}>
      <h3 style={{marginTop:0}}>Estimated UPES Walking Route</h3>
      <form onSubmit={findRoute} style={{display:"flex",gap:10,flexWrap:"wrap",alignItems:"center"}}>
        <select aria-label="Starting location" value={source} onChange={e=>setSource(e.target.value)} required>
          <option value="">Starting location</option>
          {locations.map(loc=><option key={loc.id} value={loc.id}>{loc.name}</option>)}
        </select>
        <select aria-label="Destination" value={destination} onChange={e=>setDestination(e.target.value)} required>
          <option value="">Destination</option>
          {locations.map(loc=><option key={loc.id} value={loc.id}>{loc.name}</option>)}
        </select>
        <label><input type="checkbox" checked={avoidStairs} onChange={e=>setAvoidStairs(e.target.checked)}/> Avoid stairs</label>
        <button type="submit" disabled={loading}>{loading ? "Calculating..." : "Find Route"}</button>
      </form>
      {error && <p role="alert" style={{color:"#b91c1c"}}>{error}</p>}
      {route && <div role="status">
        <p><strong>Path:</strong> {route.path_names.join(" → ")}</p>
        <p><strong>Estimated distance:</strong> {route.estimated_distance_m} m | <strong>Approx. time:</strong> {route.estimated_time_min} min</p>
        {route.contains_provisional_edges && <p style={{color:"#b45309"}}>Some connections are provisional and need on-campus verification.</p>}
        <small>Approximate straight-line map geometry; path bends and entrances are not mapped. Not suitable for turn-by-turn navigation.</small>
      </div>}
    </section>
  );
}
