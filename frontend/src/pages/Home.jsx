import { useEffect, useState } from "react";

const API = "http://localhost:5000/api";

const STATS_META = [
  { key: "critical", label: "Critical Alerts", color: "#ef4444", icon: "🔴" },
  { key: "high", label: "High Alerts", color: "#f97316", icon: "🟠" },
  { key: "medium", label: "Medium Alerts", color: "#eab308", icon: "🟡" },
  { key: "open_alerts", label: "Open Alerts", color: "#4a90e2", icon: "📬" },
  { key: "total_logs", label: "Total Logs", color: "#64748b", icon: "📜" },
  { key: "total_alerts", label: "Total Alerts", color: "#8b5cf6", icon: "🚨" },
];

const BP_CARDS = [
  { id: 1, title: "Threat Intelligence", icon: "🧠", color: "#4a90e2" },
  { id: 2, title: "Control Plane Context", icon: "🔗", color: "#06b6d4" },
  { id: 3, title: "Runtime Protection", icon: "🛡️", color: "#10b981" },
  { id: 4, title: "Cloud Expertise", icon: "👥", color: "#8b5cf6" },
  { id: 5, title: "Automate Response", icon: "⚙️", color: "#f59e0b" },
];

export default function Home({ navigate }) {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    fetch(`${API}/stats`).then(r => r.json()).then(setStats).catch(() => {});
  }, []);

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: 40 }}>
        <div style={{ fontSize: 11, color: "#4a90e2", letterSpacing: 3, marginBottom: 8 }}>CROWDSTRIKE WHITEPAPER</div>
        <h1 style={{ fontSize: 32, fontWeight: 800, color: "#f1f5f9", margin: 0, lineHeight: 1.2 }}>
          Cloud Detection and Response<br />
          <span style={{ color: "#4a90e2" }}>Survival Guide for the SOC</span>
        </h1>
        <p style={{ color: "#64748b", marginTop: 12, maxWidth: 600, lineHeight: 1.6 }}>
          An interactive simulation tool and dashboard built on CrowdStrike's CDR framework —
          covering why cloud is a prime target and the 5 best practices every SOC team needs.
        </p>
      </div>

      {/* Stats Grid */}
      {stats && (
        <div style={{ marginBottom: 40 }}>
          <div style={{ fontSize: 11, color: "#475569", letterSpacing: 2, marginBottom: 16 }}>LIVE ALERT SUMMARY</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
            {STATS_META.map(s => (
              <div key={s.key} style={{
                background: "#0d1220", border: `1px solid ${s.color}22`,
                borderRadius: 10, padding: "20px 24px",
              }}>
                <div style={{ fontSize: 22 }}>{s.icon}</div>
                <div style={{ fontSize: 32, fontWeight: 800, color: s.color, margin: "8px 0 4px" }}>{stats[s.key]}</div>
                <div style={{ fontSize: 12, color: "#64748b" }}>{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Navigation Cards */}
      <div style={{ marginBottom: 40 }}>
        <div style={{ fontSize: 11, color: "#475569", letterSpacing: 2, marginBottom: 16 }}>EXPLORE THE GUIDE</div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 16 }}>
          <div onClick={() => navigate("why-cloud")} style={{
            background: "#0d1220", border: "1px solid #1e2d45", borderRadius: 10,
            padding: 24, cursor: "pointer", gridColumn: "1 / -1",
          }}>
            <div style={{ fontSize: 28 }}>☁️</div>
            <div style={{ fontSize: 18, fontWeight: 700, color: "#e2e8f0", margin: "8px 0 6px" }}>Why Cloud is a Prime Target</div>
            <div style={{ fontSize: 13, color: "#64748b" }}>
              Explore the 6 cloud attack layers, threat statistics from the CrowdStrike 2025 Global Threat Report,
              and compare how attacks differ from traditional endpoints.
            </div>
            <div style={{ marginTop: 16, fontSize: 12, color: "#4a90e2" }}>Explore Section →</div>
          </div>
          {BP_CARDS.map(bp => (
            <div key={bp.id} onClick={() => navigate("best-practice", bp.id)} style={{
              background: "#0d1220", border: `1px solid ${bp.color}22`,
              borderRadius: 10, padding: 24, cursor: "pointer",
            }}>
              <div style={{ fontSize: 24 }}>{bp.icon}</div>
              <div style={{ fontSize: 15, fontWeight: 700, color: "#e2e8f0", margin: "8px 0 4px" }}>
                Best Practice {bp.id}
              </div>
              <div style={{ fontSize: 13, color: "#64748b" }}>{bp.title}</div>
              <div style={{ marginTop: 12, fontSize: 11, color: bp.color }}>Simulate Attack →</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
