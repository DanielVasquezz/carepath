import { useState } from "react";
import api from "./api";

export default function Login({ onLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      // FastAPI OAuth2 requires form-data, NOT JSON
      const formData = new URLSearchParams();
      formData.append("username", email);
      formData.append("password", password);

      const res = await api.post("/auth/login", formData, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });

      const token = res.data.access_token;
      localStorage.setItem("token", token);
      onLogin();
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(
        typeof detail === "string"
          ? detail
          : "Credenciales incorrectas"
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      maxWidth: 420,
      margin: "80px auto",
      padding: 40,
      border: "1px solid #e0e0e0",
      borderRadius: 16,
      boxShadow: "0 4px 24px rgba(0,0,0,0.08)",
      fontFamily: "system-ui, sans-serif",
    }}>
      <div style={{ textAlign: "center", marginBottom: 32 }}>
        <div style={{ fontSize: 48 }}>🏥</div>
        <h1 style={{ margin: "8px 0 4px", fontSize: 24, color: "#1a1a2e" }}>CarePath</h1>
        <p style={{ margin: 0, color: "#666", fontSize: 14 }}>
          Intelligent Medical Triage System
        </p>
      </div>

      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: "block", marginBottom: 6, fontWeight: 500, color: "#333" }}>
            Email
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="patient@email.com"
            required
            style={{
              width: "100%",
              padding: "12px 16px",
              border: "1.5px solid #ddd",
              borderRadius: 8,
              fontSize: 15,
              boxSizing: "border-box",
              outline: "none",
            }}
          />
        </div>

        <div style={{ marginBottom: 24 }}>
          <label style={{ display: "block", marginBottom: 6, fontWeight: 500, color: "#333" }}>
            Password
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            required
            style={{
              width: "100%",
              padding: "12px 16px",
              border: "1.5px solid #ddd",
              borderRadius: 8,
              fontSize: 15,
              boxSizing: "border-box",
              outline: "none",
            }}
          />
        </div>

        {error && (
          <div style={{
            padding: "12px 16px",
            background: "#fff0f0",
            border: "1px solid #ffcccc",
            borderRadius: 8,
            color: "#cc0000",
            marginBottom: 20,
            fontSize: 14,
          }}>
            ❌ {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          style={{
            width: "100%",
            padding: "14px",
            background: loading ? "#94a3b8" : "#2563eb",
            color: "white",
            border: "none",
            borderRadius: 8,
            fontSize: 16,
            fontWeight: 600,
            cursor: loading ? "not-allowed" : "pointer",
          }}
        >
          {loading ? "Signing in..." : "Sign In →"}
        </button>
      </form>

      <p style={{ textAlign: "center", marginTop: 20, fontSize: 13, color: "#999" }}>
        No account? Register via API at <code>/api/v1/patients/</code>
      </p>
    </div>
  );
}