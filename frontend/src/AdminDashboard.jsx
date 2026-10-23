
import { useEffect, useState } from "react";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";

import "./AdminDashboard.css";

const API_URL = "http://127.0.0.1:8000";

const COLORS = {
  low: "#16a34a",
  medium: "#f59e0b",
  high: "#dc2626",
};

function AdminDashboard({ token, onBack, onLogout }) {
  const [summary, setSummary] = useState(null);
  const [distribution, setDistribution] = useState([]);
  const [hotspots, setHotspots] = useState([]);
  const [hourly, setHourly] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function fetchAnalytics(endpoint) {
    const response = await fetch(
      `${API_URL}${endpoint}`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );

    if (response.status === 401) {
      onLogout();
      throw new Error("Session expired. Please log in.");
    }

    if (response.status === 403) {
      throw new Error(
        "Administrator access is required."
      );
    }

    if (!response.ok) {
      throw new Error("Unable to load analytics.");
    }

    return response.json();
  }

  async function loadAnalytics() {
    setLoading(true);
    setError("");

    try {
      const [
        summaryData,
        distributionData,
        hotspotsData,
        hourlyData,
      ] = await Promise.all([
        fetchAnalytics("/analytics/summary"),
        fetchAnalytics("/analytics/distribution"),
        fetchAnalytics("/analytics/hotspots"),
        fetchAnalytics("/analytics/hourly"),
      ]);

      setSummary(summaryData);
      setDistribution(distributionData);
      setHotspots(hotspotsData);
      setHourly(hourlyData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let active = true;

    async function initialLoad() {
      try {
        const endpoints = [
          "/analytics/summary",
          "/analytics/distribution",
          "/analytics/hotspots",
          "/analytics/hourly",
        ];

        const responses = await Promise.all(
          endpoints.map((endpoint) =>
            fetch(`${API_URL}${endpoint}`, {
              headers: {
                Authorization: `Bearer ${token}`,
              },
            })
          )
        );

        if (responses.some((r) => r.status === 401)) {
          onLogout();
          return;
        }

        if (responses.some((r) => r.status === 403)) {
          throw new Error(
            "Administrator access required."
          );
        }

        if (responses.some((r) => !r.ok)) {
          throw new Error("Unable to load analytics.");
        }

        const data = await Promise.all(
          responses.map((r) => r.json())
        );

        if (!active) return;

        setSummary(data[0]);
        setDistribution(data[1]);
        setHotspots(data[2]);
        setHourly(data[3]);
      } catch (err) {
        if (active) setError(err.message);
      } finally {
        if (active) setLoading(false);
      }
    }

    initialLoad();

    return () => {
      active = false;
    };
  }, [token, onLogout]);

  const cards = summary
    ? [
        ["Campus Locations", summary.total_locations],
        ["Walking Connections", summary.total_edges],
        ["Total Crowd Reports", summary.total_reports],
        ["High Crowd Reports", summary.high_crowd_reports],
      ]
    : [];

  const hourlyData = hourly.map((item) => ({
    ...item,
    label: `${String(item.hour).padStart(2, "0")}:00`,
  }));

  return (
    <div className="admin-page">
      <header className="admin-header">
        <div>
          <h1>CampusFlow Analytics</h1>
          <p>Protected Administrator Dashboard</p>
        </div>

        <div className="admin-header-actions">
          <button onClick={loadAnalytics}>
            Refresh Data
          </button>

          <button
            className="back-button"
            onClick={onBack}
          >
            Back to CampusFlow
          </button>
        </div>
      </header>

      <main className="admin-main">
        {loading && (
          <p className="admin-status">
            Loading analytics...
          </p>
        )}

        {error && (
          <p className="admin-error" role="alert">
            {error}
          </p>
        )}

        {summary && (
          <>
            <div className="admin-stats">
              {cards.map(([title, value]) => (
                <div
                  className="admin-stat-card"
                  key={title}
                >
                  <p>{title}</p>
                  <h2>{value}</h2>
                </div>
              ))}
            </div>

            <div className="admin-chart-grid">
              <section className="admin-panel">
                <h2>Crowd Distribution</h2>
                <p>Reports by congestion level</p>

                <div className="admin-chart">
                  <ResponsiveContainer
                    width="100%"
                    height="100%"
                  >
                    <PieChart>
                      <Pie
                        data={distribution}
                        dataKey="count"
                        nameKey="level"
                        cx="50%"
                        cy="50%"
                        outerRadius={105}
                        label
                      >
                        {distribution.map((entry) => (
                          <Cell
                            key={entry.level}
                            fill={COLORS[entry.level]}
                          />
                        ))}
                      </Pie>

                      <Tooltip />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </section>

              <section className="admin-panel">
                <h2>Hourly Crowd Reports</h2>
                <p>Submission times in IST</p>

                <div className="admin-chart">
                  <ResponsiveContainer
                    width="100%"
                    height="100%"
                  >
                    <BarChart data={hourlyData}>
                      <CartesianGrid
                        strokeDasharray="3 3"
                      />
                      <XAxis
                        dataKey="label"
                        interval={3}
                      />
                      <YAxis allowDecimals={false} />
                      <Tooltip />
                      <Legend />

                      <Bar
                        dataKey="low"
                        stackId="crowd"
                        fill={COLORS.low}
                      />
                      <Bar
                        dataKey="medium"
                        stackId="crowd"
                        fill={COLORS.medium}
                      />
                      <Bar
                        dataKey="high"
                        stackId="crowd"
                        fill={COLORS.high}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </section>
            </div>

            <section className="admin-panel">
              <h2>Campus Congestion Hotspots</h2>
              <p>Ranked by High crowd reports</p>

              <div className="admin-table-wrapper">
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>Location</th>
                      <th>Total Reports</th>
                      <th>High Reports</th>
                      <th>High Report Rate</th>
                    </tr>
                  </thead>

                  <tbody>
                    {hotspots.map((loc) => {
                      const rate = loc.total_reports
                        ? (
                            100 *
                            loc.high_reports /
                            loc.total_reports
                          ).toFixed(1)
                        : "0.0";

                      return (
                        <tr key={loc.location_id}>
                          <td>{loc.location_name}</td>
                          <td>{loc.total_reports}</td>
                          <td>{loc.high_reports}</td>
                          <td>{rate}%</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </section>

            <p className="admin-disclaimer">
              These analytics use voluntary and
              demonstration crowd reports, not measured
              campus occupancy.
            </p>
          </>
        )}
      </main>
    </div>
  );
}

export default AdminDashboard;
