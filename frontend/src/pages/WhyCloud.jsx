import { useEffect, useState } from "react";

const API = "http://localhost:5000/api";

const WHITEPAPER_STATS = [
  { value: "26%", label: "Increase in cloud intrusions in 2024", source: "CrowdStrike 2025 Global Threat Report", color: "#ef4444" },
  { value: "51s", label: "Fastest eCrime attacker breakout time", source: "CrowdStrike 2025 Global Threat Report", color: "#f97316" },
  { value: "48 min", label: "Average attacker breakout time (down from 62 min)", source: "CrowdStrike 2025 Global Threat Report", color: "#eab308" },
  { value: "35%", label: "Cloud incidents via abusing valid accounts (H1 2024)", source: "CrowdStrike 2025 Global Threat Report", color: "#4a90e2" },
  { value: "+50%", label: "Increase in advertised access broker listings over 2023", source: "CrowdStrike 2025 Global Threat Report", color: "#8b5cf6" },
  { value: "13%", label: "SCATTERED SPIDER's share of cloud intrusions in 2024 (down from 30%)", source: "CrowdStrike 2025 Global Threat Report", color: "#06b6d4" },
];

const COMPARE_ROWS = [
  {
    vector: "Misconfigurations",
    endpoint: "Typically require attacker to first gain a foothold on the machine before exploiting.",
    cloud: "Expose services directly to the internet at scale — no foothold needed.",
    key_diff: "Cloud misconfigurations are internet-facing from day one.",
  },
  {
    vector: "Unauthorized Access",
    endpoint: "Compromising an endpoint is limited to a single machine unless lateral movement occurs.",
    cloud: "Breaching a management console (AWS, Azure, GCP) can grant control over an entire environment.",
    key_diff: "Cloud access = infrastructure-wide blast radius.",
  },
  {
    vector: "Session Hijacking",
    endpoint: "Detected by monitoring unusual device activity or behavior on a known machine.",
    cloud: "Operates at identity & API level — valid API keys make malicious activity look legitimate.",
    key_diff: "Cloud hijacking is invisible without runtime cloud identity visibility.",
  },
];

export default function WhyCloud() {
  const [layers, setLayers] = useState([]);
  const [selected, setSelected] = useState(null);
  const [tab, setTab] = useState("stats");

  useEffect(() => {
    fetch(`${API}/layers`).then(r => r.json()).then(setLayers).catch(() => {});
  }, []);

  const RISK_COLOR = { Critical: "#ef4444", High: "#f97316", Medium: "#eab308" };

  return (
    <div>
      <div style={{ marginBottom: 32 }}>
        <div style={{ fontSize: 11, color: "#4a90e2", letterSpacing: 3, marginBottom: 8 }}>SECTION 1 OF 2</div>
        <h2 style={{ fontSize: 26, fontWeight: 800, color: "#f1f5f9", margin: 0 }}>Why Cloud is a Prime Target</h2>
        <p style={{ color: "#64748b", marginTop: 8, maxWidth: 600 }}>
          As organizations expand their cloud footprint, attackers follow. Cloud environments introduce
          new attack layers that traditional SOC tools were never built to defend.
        </p>
      </div>

      {/* Tab Bar */}
      <div style={{ display: "flex", gap: 8, marginBottom: 32 }}>
        {[["stats", "📊 Threat Stats"], ["layers", "🗂️ Attack Surface"], ["compare", "⚔️ Cloud vs Endpoint"]].map(([t, label]) => (
          <button key={t} onClick={() => setTab(t)} style={{
            padding: "8px 20px", borderRadius: 6, border: "none", cursor: "pointer", fontSize: 13,
            background: tab === t ? "#1a2744" : "#0d1220",
            color: tab === t ? "#4a90e2" : "#64748b",
            borderBottom: tab === t ? "2px solid #4a90e2" : "2px solid transparent",
          }}>{label}</button>
        ))}
      </div>

      {/* STATS TAB */}
      {tab === "stats" && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 20 }}>
          {WHITEPAPER_STATS.map((s, i) => (
            <div key={i} style={{
              background: "#0d1220", border: `1px solid ${s.color}33`,
              borderRadius: 10, padding: "24px 28px",
            }}>
              <div style={{ fontSize: 36, fontWeight: 900, color: s.color }}>{s.value}</div>
              <div style={{ fontSize: 14, color: "#cbd5e1", marginTop: 8, lineHeight: 1.5 }}>{s.label}</div>
              <div style={{ fontSize: 10, color: "#334155", marginTop: 8 }}>Source: {s.source}</div>
            </div>
          ))}
        </div>
      )}

      {/* LAYERS TAB */}
      {tab === "layers" && (
        <div>
          <p style={{ fontSize: 13, color: "#64748b", marginBottom: 20 }}>
            Click any layer to see its threat details. Cloud attacks rarely stay in one layer — adversaries move fluidly across all of them.
          </p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 16 }}>
            {layers.map(layer => (
              <div key={layer.id} onClick={() => setSelected(selected?.id === layer.id ? null : layer)}
                style={{
                  background: selected?.id === layer.id ? "#1a2744" : "#0d1220",
                  border: `1px solid ${selected?.id === layer.id ? RISK_COLOR[layer.risk] : "#1e2d45"}`,
                  borderRadius: 10, padding: 20, cursor: "pointer",
                }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span style={{ fontSize: 24 }}>{layer.icon}</span>
                    <span style={{ fontSize: 15, fontWeight: 700, color: "#e2e8f0" }}>{layer.name}</span>
                  </div>
                  <span style={{
                    fontSize: 10, padding: "3px 10px", borderRadius: 20,
                    background: `${RISK_COLOR[layer.risk]}22`, color: RISK_COLOR[layer.risk],
                  }}>{layer.risk}</span>
                </div>
                {selected?.id === layer.id && (
                  <div style={{ marginTop: 16, borderTop: "1px solid #1e2d45", paddingTop: 16 }}>
                    <p style={{ fontSize: 13, color: "#94a3b8", marginBottom: 12 }}>{layer.description}</p>
                    <div style={{ background: "#0a0e1a", borderRadius: 6, padding: 12, marginBottom: 10 }}>
                      <div style={{ fontSize: 10, color: "#ef4444", marginBottom: 4 }}>⚠️ EXAMPLE THREAT</div>
                      <div style={{ fontSize: 13, color: "#fca5a5" }}>{layer.example_threat}</div>
                    </div>
                    <div style={{ fontSize: 11, color: "#475569" }}>💡 {layer.stat}</div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* COMPARE TAB */}
      {tab === "compare" && (
        <div>
          <p style={{ fontSize: 13, color: "#64748b", marginBottom: 20 }}>
            The same attack vector plays out very differently in cloud vs endpoint environments.
          </p>
          {COMPARE_ROWS.map((row, i) => (
            <div key={i} style={{ background: "#0d1220", border: "1px solid #1e2d45", borderRadius: 10, padding: 24, marginBottom: 16 }}>
              <div style={{ fontSize: 15, fontWeight: 700, color: "#4a90e2", marginBottom: 16 }}>{row.vector}</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
                <div style={{ background: "#0a0e1a", borderRadius: 8, padding: 16 }}>
                  <div style={{ fontSize: 10, color: "#475569", marginBottom: 8 }}>🖥️ ON ENDPOINTS</div>
                  <div style={{ fontSize: 13, color: "#94a3b8", lineHeight: 1.6 }}>{row.endpoint}</div>
                </div>
                <div style={{ background: "#0a0e1a", borderRadius: 8, padding: 16 }}>
                  <div style={{ fontSize: 10, color: "#4a90e2", marginBottom: 8 }}>☁️ IN THE CLOUD</div>
                  <div style={{ fontSize: 13, color: "#94a3b8", lineHeight: 1.6 }}>{row.cloud}</div>
                </div>
              </div>
              <div style={{ background: "#1a2744", borderRadius: 6, padding: 12 }}>
                <span style={{ fontSize: 10, color: "#4a90e2" }}>KEY DIFFERENCE: </span>
                <span style={{ fontSize: 12, color: "#cbd5e1" }}>{row.key_diff}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
