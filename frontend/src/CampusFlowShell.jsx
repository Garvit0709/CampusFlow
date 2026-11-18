
import { useState } from "react";

import BidholiMap from "./BidholiMap";
import AuthPage from "./AuthPage";
import AdminDashboard from "./AdminDashboard";

function CampusFlowShell() {
  const [view, setView] = useState("map");
  const [session, setSession] = useState(null);

  const user = session?.user;
  const token = session?.token;
  const isAdmin = user?.role === "admin";

  function handleLogin(loginSession) {
    setSession(loginSession);

    setView(
      loginSession?.user?.role === "admin"
        ? "admin"
        : "map"
    );
  }

  function handleLogout() {
    setSession(null);
    setView("map");
  }

  // Optional login screen
  if (view === "login") {
    return (
      <div>
        <button
          type="button"
          onClick={() => setView("map")}
        >
          Back to Public Map
        </button>

        <AuthPage onLogin={handleLogin} />
      </div>
    );
  }

  // Protected admin dashboard
  if (view === "admin" && isAdmin && token) {
    return (
      <AdminDashboard
        token={token}
        onBack={() => setView("map")}
        onLogout={handleLogout}
      />
    );
  }

  // Public Bidholi map
  return (
    <BidholiMap
      accountControls={
        <div className="cf-account-actions">
          {isAdmin && (
            <button
              type="button"
              onClick={() => setView("admin")}
            >
              Admin Dashboard
            </button>
          )}

          {session ? (
            <button
              type="button"
              onClick={handleLogout}
            >
              Logout
            </button>
          ) : (
            <button
              type="button"
              onClick={() => setView("login")}
            >
              Sign In
            </button>
          )}
        </div>
      }
    />
  );
}

export default CampusFlowShell;
