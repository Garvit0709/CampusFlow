
import { useState } from "react";
import "./AuthPage.css";

const API_URL = "http://127.0.0.1:8000";

function AuthPage({ onLogin }) {
  const [mode, setMode] = useState("login");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function readResponse(response) {
    const data = await response.json();

    if (!response.ok) {
      const message =
        typeof data.detail === "string"
          ? data.detail
          : "Request failed";

      throw new Error(message);
    }

    return data;
  }

  async function handleSubmit(event) {
    event.preventDefault();

    setError("");
    setSuccess("");

    if (mode === "register") {
      if (fullName.trim().length < 2) {
        setError("Enter your full name.");
        return;
      }

      if (password.length < 12) {
        setError("Password must contain at least 12 characters.");
        return;
      }

      if (password !== confirmPassword) {
        setError("Passwords do not match.");
        return;
      }
    }

    setLoading(true);

    try {
      if (mode === "register") {
        const response = await fetch(
          `${API_URL}/auth/register`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              full_name: fullName.trim(),
              email: email.trim(),
              password,
            }),
          }
        );

        await readResponse(response);

        setSuccess(
          "Student account created! Please log in."
        );
        setMode("login");
        setPassword("");
        setConfirmPassword("");
      } else {
        const response = await fetch(
          `${API_URL}/auth/login`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              email: email.trim(),
              password,
            }),
          }
        );

        const data = await readResponse(response);

        if (!data.access_token) {
          throw new Error("Login response has no access token.");
        }

        // Verify the token and retrieve the current role
        const verifyResponse = await fetch(
          `${API_URL}/auth/me`,
          {
            headers: {
              Authorization: `Bearer ${data.access_token}`,
            },
          }
        );

        const user = await readResponse(verifyResponse);

        onLogin({
          token: data.access_token,
          user,
        });
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function switchMode(nextMode) {
    setMode(nextMode);
    setError("");
    setSuccess("");
    setPassword("");
    setConfirmPassword("");
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-brand">
          <div className="auth-logo">CF</div>
          <h1>CampusFlow</h1>
          <p>Intelligent Campus Navigation Platform</p>
        </div>

        <div className="auth-tabs">
          <button
            type="button"
            className={mode === "login" ? "active" : ""}
            onClick={() => switchMode("login")}
          >
            Login
          </button>

          <button
            type="button"
            className={mode === "register" ? "active" : ""}
            onClick={() => switchMode("register")}
          >
            Register
          </button>
        </div>

        <h2>
          {mode === "login"
            ? "Welcome Back"
            : "Create Student Account"}
        </h2>

        <p className="auth-subtitle">
          {mode === "login"
            ? "Sign in to continue to CampusFlow."
            : "Register to access campus navigation."}
        </p>

        <form onSubmit={handleSubmit}>
          {mode === "register" && (
            <div className="auth-field">
              <label htmlFor="auth-name">Full Name</label>
              <input
                id="auth-name"
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Enter your full name"
                autoComplete="name"
                required
                minLength={2}
                maxLength={120}
              />
            </div>
          )}

          <div className="auth-field">
            <label htmlFor="auth-email">Email Address</label>
            <input
              id="auth-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Enter your email"
              autoComplete="email"
              required
            />
          </div>

          <div className="auth-field">
            <label htmlFor="auth-password">Password</label>
            <input
              id="auth-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              autoComplete={
                mode === "login"
                  ? "current-password"
                  : "new-password"
              }
              required
              minLength={mode === "register" ? 12 : undefined}
            />
          </div>

          {mode === "register" && (
            <div className="auth-field">
              <label htmlFor="auth-confirm">
                Confirm Password
              </label>
              <input
                id="auth-confirm"
                type="password"
                value={confirmPassword}
                onChange={(e) =>
                  setConfirmPassword(e.target.value)
                }
                placeholder="Confirm your password"
                autoComplete="new-password"
                required
              />
            </div>
          )}

          {error && (
            <p className="auth-error" role="alert">
              {error}
            </p>
          )}

          {success && (
            <p className="auth-success" role="status">
              {success}
            </p>
          )}

          <button
            className="auth-submit"
            type="submit"
            disabled={loading}
          >
            {loading
              ? "Please wait..."
              : mode === "login"
                ? "Sign In"
                : "Create Account"}
          </button>
        </form>

        <p className="auth-footer">
          {mode === "login"
            ? "New to CampusFlow?"
            : "Already have an account?"}{" "}
          <button
            type="button"
            onClick={() =>
              switchMode(
                mode === "login" ? "register" : "login"
              )
            }
          >
            {mode === "login" ? "Register" : "Login"}
          </button>
        </p>

        <p className="auth-note">
          Administrator accounts are created separately
          by the system administrator.
        </p>
      </div>
    </div>
  );
}

export default AuthPage;
