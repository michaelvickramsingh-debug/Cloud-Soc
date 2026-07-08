import { useEffect, useState } from "react";

const API = "http://localhost:5000/api";
const SEV_COLOR = { Critical: "#ef4444", High: "#f97316", Medium: "#eab308", Low: "#22c55e" };

export default function Logs() {
  const [logs, setLogs] = useState([]);
  const [search, setSearch] = useState("");

  useEffect(() => {
    fetch(`${API}/logs`).then(r => r.json()).then(setLogs).catch(() => {});
  }, []);

  const filtered = logs.filter(l =>
    !search || l.action.toLowerCase().includes(search.toLowerCase()) ||
    l.user.toLowerCase().includes(search.toLowerCase()) ||
    l.cloud_service.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div>
      <div style={{ marginBottom: 28 }}>
        <div style={{ fontSize: 11, color: "#4a90e2", letterSpacing: 3, marginBottom: 8 }}>AUDIT TRAIL</div>
        <h2 style={{ fontSize: 26, fontWeight: 800, color: "#f1f5f9", margin: 0 }}>📜 Cloud Log Viewer</h2>
        <p style={{ color: "#64748b", marginTop: 8 }}>All simulated cloud activity logs. Logs are generated when you run attack simulations.</p>
      </div>

      <input
        value={search} onChange={e => setSearch(e.target.value)}
        placeholder="Search by action, user, or service..."
        style={{
          width: "100%", padding: "10px 16px", borderRadius: 8,
          background: "#0d1220", border: "1px solid #1e2d45",
          color: "#e2e8f0", fontSize: 13, marginBottom: 24, boxSizing: "border-box",
          outline: "none",
        }}
      />

      <div style={{ fontSize: 12, color: "#475569", marginBottom: 16 }}>
        Showing {filtered.length} of {logs.length} log entries
      </div>

      {filtered.length === 0 ? (
        <div style={{ textAlign: "center", padding: 60, color: "#334155" }}>
          <div style={{ fontSize: 32, marginBottom: 12 }}>📭</div>
          <div style={{ fontSize: 16, fontWeight: 600 }}>No logs yet</div>
          <div style={{ fontSize: 13, marginTop: 8 }}>Run a simulation from any Best Practice page to generate logs.</div>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {filtered.map(log => (
            <div key={log.id} style={{
              background: "#0d1220",
              borderLeft: `3px solid ${log.is_malicious ? (SEV_COLOR[log.severity] || "#64748b") : "#1e2d45"}`,
              borderRadius: "0 8px 8px 0", padding: "10px 16px",
              display: "grid",
              gridTemplateColumns: "100px 160px 1fr 100px 120px",
              gap: 12, alignItems: "center", fontSize: 12,
            }}>
              <span style={{ color: SEV_COLOR[log.severity] || "#64748b", fontWeight: 700 }}>{log.severity}</span>
              <span style={{ color: "#64748b" }}>{log.user}</span>
              <span style={{ color: "#94a3b8" }}>{log.action}</span>
              <span style={{ color: "#475569" }}>{log.cloud_service}</span>
              <span style={{ color: "#334155" }}>{log.region}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
