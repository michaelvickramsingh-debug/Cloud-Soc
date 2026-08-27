import { useEffect, useState, useRef } from "react";
import io from "socket.io-client";

const API = "http://localhost:5001/api";
const SOCKET_URL = "http://localhost:5001";
const SEV_COLOR = { Critical: "#ef4444", High: "#f97316", Medium: "#eab308", Low: "#22c55e" };

export default function Logs() {
  const [logs, setLogs] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [search, setSearch] = useState("");
  const [isLive, setIsLive] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState("disconnected");
  const socketRef = useRef(null);

  // Load initial logs from API
  useEffect(() => {
    fetch(`${API}/logs`)
      .then(r => r.json())
      .then(data => {
        setLogs(Array.isArray(data) ? data : []);
      })
      .catch(err => console.error("Failed to load logs:", err));
  }, []);

  // Setup WebSocket connection for live logs
  useEffect(() => {
    if (!isLive) return;

    const socket = io(SOCKET_URL, {
      path: "/socket.io",
      transports: ["websocket", "polling"],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      reconnectionAttempts: 5,
    });

    socketRef.current = socket;

    socket.on("connect", () => {
      console.log("Connected to log stream");
      setConnectionStatus("connected");
      socket.emit("subscribe", { filters: {} }, (response) => {
        console.log("Subscribed:", response);
      });
    });

    socket.on("new_logs", (data) => {
      console.log("Received new logs:", data);
      setLogs(prev => [...data.logs, ...prev].slice(0, 1000)); // Keep last 1000
    });

    socket.on("new_alert", (alert) => {
      console.log("Received alert:", alert);
      setAlerts(prev => [alert, ...prev].slice(0, 100)); // Keep last 100 alerts
    });

    socket.on("ingestion_complete", (stats) => {
      console.log("Log ingestion complete:", stats);
    });

    socket.on("disconnect", () => {
      console.log("Disconnected from log stream");
      setConnectionStatus("disconnected");
    });

    socket.on("error", (error) => {
      console.error("Socket error:", error);
      setConnectionStatus("error");
    });

    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
    };
  }, [isLive]);

  const filtered = logs.filter(l =>
    !search ||
    (l.event && l.event.toLowerCase().includes(search.toLowerCase())) ||
    (l.user && l.user.toLowerCase().includes(search.toLowerCase())) ||
    (l.source && l.source.toLowerCase().includes(search.toLowerCase()))
  );

  const toggleLive = () => {
    setIsLive(!isLive);
  };

  const connectionColor = {
    connected: "#22c55e",
    disconnected: "#64748b",
    error: "#ef4444"
  }[connectionStatus];

  return (
    <div>
      <div style={{ marginBottom: 28 }}>
        <div style={{ fontSize: 11, color: "#4a90e2", letterSpacing: 3, marginBottom: 8 }}>AUDIT TRAIL</div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={{ fontSize: 26, fontWeight: 800, color: "#f1f5f9", margin: 0 }}>📜 Cloud Log Viewer</h2>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <button
              onClick={toggleLive}
              style={{
                padding: "8px 16px",
                borderRadius: 6,
                border: "none",
                background: isLive ? "#ef4444" : "#4a90e2",
                color: "white",
                cursor: "pointer",
                fontSize: 13,
                fontWeight: 600,
              }}
            >
              {isLive ? "🔴 Stop Live" : "🟢 Go Live"}
            </button>
            <div style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              padding: "6px 12px",
              borderRadius: 6,
              background: "#0d1220",
              border: `1px solid ${connectionColor}`,
            }}>
              <div style={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                background: connectionColor,
              }} />
              <span style={{ fontSize: 12, color: connectionColor }}>
                {connectionStatus === "connected" ? "Live" : connectionStatus === "disconnected" ? "Offline" : "Error"}
              </span>
            </div>
          </div>
        </div>
        <p style={{ color: "#64748b", marginTop: 8 }}>
          {isLive
            ? "Real-time cloud activity logs from AWS CloudTrail"
            : "All simulated cloud activity logs. Logs are generated when you run attack simulations."}
        </p>
      </div>

      <input
        value={search}
        onChange={e => setSearch(e.target.value)}
        placeholder="Search by event, user, or service..."
        style={{
          width: "100%",
          padding: "10px 16px",
          borderRadius: 8,
          background: "#0d1220",
          border: "1px solid #1e2d45",
          color: "#e2e8f0",
          fontSize: 13,
          marginBottom: 24,
          boxSizing: "border-box",
          outline: "none",
        }}
      />

      <div style={{ fontSize: 12, color: "#475569", marginBottom: 16 }}>
        Showing {filtered.length} of {logs.length} log entries
        {alerts.length > 0 && ` • ${alerts.length} alerts`}
      </div>

      {alerts.length > 0 && (
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 12, color: "#ef4444", fontWeight: 600, marginBottom: 8 }}>🚨 Recent Alerts</div>
          {alerts.slice(0, 3).map((alert, idx) => (
            <div key={idx} style={{
              background: "#1a0a0a",
              border: "1px solid #ef4444",
              borderRadius: 6,
              padding: "10px 12px",
              marginBottom: 8,
              fontSize: 12,
            }}>
              <div style={{ color: "#ef4444", fontWeight: 600 }}>{alert.title}</div>
              <div style={{ color: "#94a3b8", marginTop: 4 }}>{alert.description}</div>
            </div>
          ))}
        </div>
      )}

      {filtered.length === 0 ? (
        <div style={{ textAlign: "center", padding: 60, color: "#334155" }}>
          <div style={{ fontSize: 32, marginBottom: 12 }}>📭</div>
          <div style={{ fontSize: 16, fontWeight: 600 }}>No logs yet</div>
          <div style={{ fontSize: 13, marginTop: 8 }}>
            {isLive
              ? "Waiting for live CloudTrail events..."
              : "Run a simulation from any Best Practice page to generate logs."}
          </div>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {filtered.map(log => (
            <div key={log.id} style={{
              background: "#0d1220",
              borderLeft: `3px solid ${log.severity ? SEV_COLOR[log.severity] : "#1e2d45"}`,
              borderRadius: "0 8px 8px 0",
              padding: "10px 16px",
              display: "grid",
              gridTemplateColumns: "100px 140px 1fr 100px 120px",
              gap: 12,
              alignItems: "center",
              fontSize: 12,
            }}>
              <span style={{ color: log.severity ? SEV_COLOR[log.severity] : "#64748b", fontWeight: 700 }}>
                {log.severity || "Info"}
              </span>
              <span style={{ color: "#64748b" }}>{log.user || "—"}</span>
              <span style={{ color: "#94a3b8" }}>{log.event || log.action || "—"}</span>
              <span style={{ color: "#475569" }}>{log.source || "—"}</span>
              <span style={{ color: "#334155" }}>{log.region || "—"}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
