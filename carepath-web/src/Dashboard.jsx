import { useEffect, useState } from "react";
import api from "./api";

const PRIORITY_CONFIG = {
  P1_immediate: { label: "P1 — IMMEDIATE", color: "#dc2626", bg: "#fef2f2", icon: "🚨" },
  P2_urgent:    { label: "P2 — URGENT",    color: "#ea580c", bg: "#fff7ed", icon: "⚠️" },
  P3_delayed:   { label: "P3 — DELAYED",   color: "#ca8a04", bg: "#fefce8", icon: "⏳" },
  P4_minimal:   { label: "P4 — MINIMAL",   color: "#16a34a", bg: "#f0fdf4", icon: "✅" },
  null:         { label: "Not evaluated",  color: "#6b7280", bg: "#f9fafb", icon: "⬜" },
};

const STATUS_COLOR = {
  open:       "#2563eb",
  in_review:  "#ca8a04",
  resolved:   "#16a34a",
  escalated:  "#dc2626",
};

export default function Dashboard({ onLogout }) {
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [creating, setCreating] = useState(false);
  const [evaluating, setEvaluating] = useState(null);
  const [showForm, setShowForm] = useState(false);

  const [form, setForm] = useState({
    chief_complaint: "",
    symptom_description: "",
    severity: "moderate",
    duration_hours: "",
    body_location: "",
    is_worsening: false,
  });

  const fetchCases = async () => {
    try {
      setLoading(true);
      setError(null);
      // Get patient's own cases — no general list endpoint exists
      // We use the cases list from the patient's perspective
      // Each patient sees their own cases via individual GETs
      // For now we store them locally after creation
      setLoading(false);
    } catch (err) {
      setError("Error loading cases");
      setLoading(false);
    }
  };

  useEffect(() => {
    // Load cases from localStorage cache
    const cached = localStorage.getItem("carepath_cases");
    if (cached) {
      try { setCases(JSON.parse(cached)); } catch {}
    }
    setLoading(false);
  }, []);

  const saveCases = (updated) => {
    setCases(updated);
    localStorage.setItem("carepath_cases", JSON.stringify(updated));
  };

  const handleCreateCase = async (e) => {
    e.preventDefault();
    setCreating(true);

    try {
      const payload = {
        chief_complaint: form.chief_complaint,
        symptoms: [{
          description: form.symptom_description,
          severity: form.severity,
          duration_hours: form.duration_hours ? parseFloat(form.duration_hours) : null,
          body_location: form.body_location || null,
          is_worsening: form.is_worsening,
        }],
      };

      const res = await api.post("/cases/", payload);
      const newCase = res.data;

      saveCases([newCase, ...cases]);
      setShowForm(false);
      setForm({
        chief_complaint: "",
        symptom_description: "",
        severity: "moderate",
        duration_hours: "",
        body_location: "",
        is_worsening: false,
      });
    } catch (err) {
      const detail = err.response?.data?.detail;
      alert("Error creating case: " + (typeof detail === "string" ? detail : JSON.stringify(detail)));
    } finally {
      setCreating(false);
    }
  };

  const handleEvaluate = async (caseId) => {
    setEvaluating(caseId);
    try {
      const res = await api.post(`/cases/${caseId}/evaluate`);
      const updated = cases.map((c) => c.id === caseId ? res.data : c);
      saveCases(updated);
    } catch (err) {
      const detail = err.response?.data?.detail;
      alert("Evaluation error: " + (typeof detail === "string" ? detail : "Unknown error"));
    } finally {
      setEvaluating(null);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("carepath_cases");
    onLogout();
  };

  const priorityInfo = (p) => PRIORITY_CONFIG[p] || PRIORITY_CONFIG[null];

  if (loading) return (
    <div style={{ textAlign: "center", padding: 80, fontFamily: "system-ui" }}>
      <div style={{ fontSize: 40 }}>🏥</div>
      <p>Loading CarePath...</p>
    </div>
  );

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", minHeight: "100vh", background: "#f8fafc" }}>
      {/* Header */}
      <div style={{
        background: "white",
        borderBottom: "1px solid #e2e8f0",
        padding: "16px 32px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        position: "sticky",
        top: 0,
        zIndex: 10,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 28 }}>🏥</span>
          <div>
            <h1 style={{ margin: 0, fontSize: 20, fontWeight: 700, color: "#1e293b" }}>CarePath</h1>
            <p style={{ margin: 0, fontSize: 12, color: "#94a3b8" }}>Medical Triage System</p>
          </div>
        </div>
        <div style={{ display: "flex", gap: 12 }}>
          <button
            onClick={() => setShowForm(!showForm)}
            style={{
              padding: "10px 20px",
              background: "#2563eb",
              color: "white",
              border: "none",
              borderRadius: 8,
              fontWeight: 600,
              cursor: "pointer",
              fontSize: 14,
            }}
          >
            {showForm ? "✕ Cancel" : "+ New Case"}
          </button>
          <button
            onClick={handleLogout}
            style={{
              padding: "10px 16px",
              background: "transparent",
              color: "#64748b",
              border: "1px solid #e2e8f0",
              borderRadius: 8,
              cursor: "pointer",
              fontSize: 14,
            }}
          >
            Logout
          </button>
        </div>
      </div>

      <div style={{ maxWidth: 800, margin: "0 auto", padding: "32px 16px" }}>
        {/* New Case Form */}
        {showForm && (
          <div style={{
            background: "white",
            borderRadius: 12,
            padding: 28,
            marginBottom: 24,
            border: "1px solid #e2e8f0",
            boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
          }}>
            <h2 style={{ margin: "0 0 20px", fontSize: 18, color: "#1e293b" }}>
              🏥 Open New Triage Case
            </h2>
            <form onSubmit={handleCreateCase}>
              <div style={{ marginBottom: 16 }}>
                <label style={{ display: "block", marginBottom: 6, fontWeight: 500, fontSize: 14, color: "#374151" }}>
                  Chief Complaint *
                </label>
                <input
                  value={form.chief_complaint}
                  onChange={(e) => setForm({ ...form, chief_complaint: e.target.value })}
                  placeholder="Main reason for seeking care (min 10 chars)"
                  required
                  minLength={10}
                  style={inputStyle}
                />
              </div>

              <div style={{ marginBottom: 16 }}>
                <label style={{ display: "block", marginBottom: 6, fontWeight: 500, fontSize: 14, color: "#374151" }}>
                  Symptom Description *
                </label>
                <textarea
                  value={form.symptom_description}
                  onChange={(e) => setForm({ ...form, symptom_description: e.target.value })}
                  placeholder="Describe your symptoms in detail (min 10 chars)"
                  required
                  minLength={10}
                  rows={3}
                  style={{ ...inputStyle, resize: "vertical" }}
                />
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
                <div>
                  <label style={{ display: "block", marginBottom: 6, fontWeight: 500, fontSize: 14, color: "#374151" }}>
                    Severity *
                  </label>
                  <select
                    value={form.severity}
                    onChange={(e) => setForm({ ...form, severity: e.target.value })}
                    style={inputStyle}
                  >
                    <option value="low">🟢 Low</option>
                    <option value="moderate">🟡 Moderate</option>
                    <option value="high">🟠 High</option>
                    <option value="critical">🔴 Critical</option>
                  </select>
                </div>
                <div>
                  <label style={{ display: "block", marginBottom: 6, fontWeight: 500, fontSize: 14, color: "#374151" }}>
                    Duration (hours)
                  </label>
                  <input
                    type="number"
                    value={form.duration_hours}
                    onChange={(e) => setForm({ ...form, duration_hours: e.target.value })}
                    placeholder="e.g. 2.5"
                    min={0}
                    step={0.5}
                    style={inputStyle}
                  />
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: 16, marginBottom: 20, alignItems: "end" }}>
                <div>
                  <label style={{ display: "block", marginBottom: 6, fontWeight: 500, fontSize: 14, color: "#374151" }}>
                    Body Location
                  </label>
                  <input
                    value={form.body_location}
                    onChange={(e) => setForm({ ...form, body_location: e.target.value })}
                    placeholder="e.g. chest, head, abdomen"
                    style={inputStyle}
                  />
                </div>
                <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer", paddingBottom: 12 }}>
                  <input
                    type="checkbox"
                    checked={form.is_worsening}
                    onChange={(e) => setForm({ ...form, is_worsening: e.target.checked })}
                    style={{ width: 16, height: 16 }}
                  />
                  <span style={{ fontSize: 14, color: "#374151" }}>Getting worse?</span>
                </label>
              </div>

              <button
                type="submit"
                disabled={creating}
                style={{
                  width: "100%",
                  padding: "12px",
                  background: creating ? "#94a3b8" : "#2563eb",
                  color: "white",
                  border: "none",
                  borderRadius: 8,
                  fontWeight: 600,
                  fontSize: 15,
                  cursor: creating ? "not-allowed" : "pointer",
                }}
              >
                {creating ? "⏳ Opening case..." : "Open Triage Case →"}
              </button>
            </form>
          </div>
        )}

        {/* Error */}
        {error && (
          <div style={{ padding: 16, background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 8, color: "#dc2626", marginBottom: 20 }}>
            {error}
          </div>
        )}

        {/* Cases List */}
        <div>
          <h2 style={{ fontSize: 16, fontWeight: 600, color: "#64748b", margin: "0 0 16px", textTransform: "uppercase", letterSpacing: "0.05em" }}>
            Your Cases ({cases.length})
          </h2>

          {cases.length === 0 ? (
            <div style={{
              textAlign: "center",
              padding: "60px 20px",
              background: "white",
              borderRadius: 12,
              border: "1px dashed #cbd5e1",
            }}>
              <div style={{ fontSize: 48, marginBottom: 16 }}>📋</div>
              <h3 style={{ margin: "0 0 8px", color: "#1e293b" }}>No cases yet</h3>
              <p style={{ margin: 0, color: "#94a3b8" }}>
                Click "+ New Case" to open your first triage case
              </p>
            </div>
          ) : (
            cases.map((c) => {
              const pInfo = priorityInfo(c.priority);
              const isEval = evaluating === c.id;
              const canEvaluate = c.status === "open";

              return (
                <div key={c.id} style={{
                  background: "white",
                  border: "1px solid #e2e8f0",
                  borderRadius: 12,
                  padding: 20,
                  marginBottom: 12,
                  boxShadow: "0 1px 4px rgba(0,0,0,0.04)",
                }}>
                  {/* Case header */}
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
                    <div style={{ flex: 1 }}>
                      <p style={{ margin: "0 0 6px", fontWeight: 600, color: "#1e293b", fontSize: 15 }}>
                        {c.chief_complaint}
                      </p>
                      <p style={{ margin: 0, fontSize: 12, color: "#94a3b8" }}>
                        {new Date(c.opened_at).toLocaleString()} · ID: {c.id.slice(0, 8)}...
                      </p>
                    </div>
                    <span style={{
                      padding: "4px 10px",
                      background: STATUS_COLOR[c.status] + "15",
                      color: STATUS_COLOR[c.status] || "#6b7280",
                      borderRadius: 20,
                      fontSize: 12,
                      fontWeight: 600,
                      textTransform: "uppercase",
                      whiteSpace: "nowrap",
                      marginLeft: 12,
                    }}>
                      {c.status}
                    </span>
                  </div>

                  {/* Priority badge */}
                  {c.priority && (
                    <div style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 6,
                      padding: "6px 12px",
                      background: pInfo.bg,
                      color: pInfo.color,
                      borderRadius: 8,
                      fontSize: 13,
                      fontWeight: 700,
                      marginBottom: 12,
                      border: `1px solid ${pInfo.color}30`,
                    }}>
                      {pInfo.icon} {pInfo.label}
                      {c.total_risk_score !== undefined && (
                        <span style={{ opacity: 0.7, fontWeight: 400 }}>
                          · score: {c.total_risk_score}
                        </span>
                      )}
                    </div>
                  )}

                  {/* Symptoms */}
                  {c.symptoms?.length > 0 && (
                    <div style={{ marginBottom: 12 }}>
                      {c.symptoms.map((s) => (
                        <div key={s.id} style={{
                          display: "flex",
                          gap: 8,
                          padding: "8px 12px",
                          background: "#f8fafc",
                          borderRadius: 6,
                          marginBottom: 4,
                          fontSize: 13,
                          color: "#374151",
                        }}>
                          <span>•</span>
                          <div>
                            <strong>{s.severity?.toUpperCase()}</strong>
                            {s.body_location && ` — ${s.body_location}`}
                            {s.is_worsening && " ↑ worsening"}
                            <br />
                            {s.description}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* AI Recommendation */}
                  {c.ai_recommendation && (
                    <div style={{
                      padding: "12px 16px",
                      background: "#f0f9ff",
                      border: "1px solid #bae6fd",
                      borderRadius: 8,
                      fontSize: 13,
                      color: "#0369a1",
                      marginBottom: 12,
                      lineHeight: 1.6,
                    }}>
                      <strong>🤖 AI Recommendation:</strong>
                      <br />
                      <span style={{ whiteSpace: "pre-wrap" }}>{c.ai_recommendation}</span>
                    </div>
                  )}

                  {/* Actions */}
                  {canEvaluate && (
                    <button
                      onClick={() => handleEvaluate(c.id)}
                      disabled={isEval}
                      style={{
                        padding: "8px 16px",
                        background: isEval ? "#94a3b8" : "#7c3aed",
                        color: "white",
                        border: "none",
                        borderRadius: 6,
                        fontWeight: 600,
                        fontSize: 13,
                        cursor: isEval ? "not-allowed" : "pointer",
                      }}
                    >
                      {isEval ? "⏳ Evaluating with AI..." : "🧠 Run AI Triage"}
                    </button>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}

const inputStyle = {
  width: "100%",
  padding: "10px 14px",
  border: "1.5px solid #e2e8f0",
  borderRadius: 8,
  fontSize: 14,
  boxSizing: "border-box",
  outline: "none",
  color: "#1e293b",
  background: "white",
};