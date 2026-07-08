import { useEffect, useState } from "react";

const API = "http://localhost:5000/api";

const SEV_COLOR = { Critical: "#ef4444", High: "#f97316", Medium: "#eab308", Low: "#22c55e" };
const BP_COLOR = { 1: "#4a90e2", 2: "#06b6d4", 3: "#10b981", 4: "#8b5cf6", 5: "#f59e0b" };
const BP_ICON = { 1: "🧠", 2: "🔗", 3: "🛡️", 4: "👥", 5: "⚙️" };

export default function BestPractice({ id }) {
  const [practice, setPractice] = useState(null);
  const [simResult, setSimResult] = useState(null);
  const [simLoading, setSimLoading] = useState(false);
  const [step, setStep] = useState("idle"); // idle | running | done

  useEffect(() => {
    fetch(`${API}/practices`).then(r => r.json()).then(data => {
      setPractice(data.find(p => p.id === id));
    }).catch(() => {});
    setSimResult(null);
    setStep("idle");
  }, [id]);

  const runSim = async () => {
    setSimLoading(true);
    setStep("running");
    setSimResult(null);
    try {
      const res = await fetch(`${API}/simulate/${id}`, { method: "POST" });
      const data = await res.json();
      setSimResult(data);
      setStep("done");
    } catch {
      setStep("idle");
    }
    setSimLoading(false);
  };

  if (!practice) return <div style={{ color: "#64748b", padding: 40 }}>Loading...</div>;

  const color = BP_COLOR[id];

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: 32 }}>
        <div style={{ fontSize: 11, color, letterSpacing: 3, marginBottom: 8 }}>
          BEST PRACTICE {id} OF 5
        </div>
        <h2 style={{ fontSize: 26, fontWeight: 800, color: "#f1f5f9", margin: 0 }}>
          {BP_ICON[id]} {practice.title}
        </h2>
        <p style={{ color: "#64748b", marginTop: 8, maxWidth: 700, lineHeight: 1.6 }}>
          {practice.summary}
        </p>
      </div>

      {/* Key Insight */}
      <div style={{
        background: `${color}11`, border: `1px solid ${color}44`,
        borderRadius: 10, padding: "16px 20px", marginBottom: 28,
        display: "flex", alignItems: "flex-start", gap: 12,
      }}>
        <span style={{ fontSize: 20 }}>💡</span>
        <div>
          <div style={{ fontSize: 10, color, letterSpacing: 2, marginBottom: 4 }}>KEY INSIGHT FROM WHITEPAPER</div>
          <div style={{ fontSize: 14, color: "#e2e8f0", fontWeight: 600 }}>{practice.key_insight}</div>
        </div>
      </div>

      {/* Without vs With */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 32 }}>
        <div style={{ background: "#0d1220", border: "1px solid #ef444433", borderRadius: 10, padding: 20 }}>
          <div style={{ fontSize: 10, color: "#ef4444", letterSpacing: 2, marginBottom: 12 }}>❌ WITHOUT THIS PRACTICE</div>
          <p style={{ fontSize: 13, color: "#94a3b8", lineHeight: 1.7, margin: 0 }}>{practice.what_without}</p>
        </div>
        <div style={{ background: "#0d1220", border: `1px solid ${color}33`, borderRadius: 10, padding: 20 }}>
          <div style={{ fontSize: 10, color, letterSpacing: 2, marginBottom: 12 }}>✅ WITH THIS PRACTICE</div>
          <p style={{ fontSize: 13, color: "#94a3b8", lineHeight: 1.7, margin: 0 }}>{practice.what_with}</p>
        </div>
      </div>

      {/* Simulation Section */}
      <div style={{ background: "#0d1220", border: "1px solid #1e2d45", borderRadius: 12, padding: 28 }}>
        <div style={{ fontSize: 11, color: "#475569", letterSpacing: 2, marginBottom: 4 }}>INTERACTIVE SIMULATION</div>
        <h3 style={{ fontSize: 18, fontWeight: 700, color: "#e2e8f0", margin: "0 0 8px" }}>
          Simulate Attack Scenario {id}
        </h3>
        <p style={{ fontSize: 13, color: "#64748b", marginBottom: 24 }}>
          This simulation generates realistic cloud attack logs and runs the detection engine to produce alerts — demonstrating what the SOC would see.
        </p>

        <button onClick={runSim} disabled={simLoading} style={{
          padding: "12px 32px", borderRadius: 8, border: "none",
          background: simLoading ? "#1e2d45" : color,
          color: simLoading ? "#64748b" : "#fff",
          fontSize: 14, fontWeight: 700, cursor: simLoading ? "not-allowed" : "pointer",
          marginBottom: 28,
        }}>
          {simLoading ? "⏳ Running Simulation..." : `🚀 Run Attack Simulation ${id}`}
        </button>

        {/* Running State */}
        {step === "running" && (
          <div style={{ display: "flex", gap: 8, alignItems: "center", color: "#64748b", fontSize: 13 }}>
            <span>⚙️</span> Generating logs → Running detection engine → Writing alerts...
          </div>
        )}

        {/* Results */}
        {step === "done" && simResult && (
          <div>
            {/* Summary Banner */}
            <div style={{
              background: "#0a0e1a", borderRadius: 8, padding: 16,
              display: "flex", gap: 32, marginBottom: 24,
              border: `1px solid ${color}33`,
            }}>
              <div>
                <div style={{ fontSize: 28, fontWeight: 900, color }}>{simResult.logs_generated}</div>
                <div style={{ fontSize: 11, color: "#64748b" }}>Logs Generated</div>
              </div>
              <div>
                <div style={{ fontSize: 28, fontWeight: 900, color: "#ef4444" }}>{simResult.alerts_generated}</div>
                <div style={{ fontSize: 11, color: "#64748b" }}>Alerts Triggered</div>
              </div>
              <div>
                <div style={{ fontSize: 28, fontWeight: 900, color: "#22c55e" }}>✓</div>
                <div style={{ fontSize: 11, color: "#64748b" }}>Attack Detected</div>
              </div>
            </div>

            {/* Logs */}
            <div style={{ marginBottom: 24 }}>
              <div style={{ fontSize: 11, color: "#475569", letterSpacing: 2, marginBottom: 12 }}>GENERATED ATTACK LOGS</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {simResult.logs.map((log, i) => (
                  <div key={i} style={{
                    background: "#0a0e1a", borderRadius: 6, padding: "10px 14px",
                    borderLeft: `3px solid ${SEV_COLOR[log.severity] || "#64748b"}`,
                    fontSize: 12,
                  }}>
                    <span style={{ color: SEV_COLOR[log.severity], fontWeight: 700 }}>[{log.severity}]</span>
                    <span style={{ color: "#94a3b8", marginLeft: 8 }}>{log.action}</span>
                    <span style={{ color: "#475569", marginLeft: 12 }}>| {log.user} | {log.cloud_service} | {log.region}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Alerts */}
            <div>
              <div style={{ fontSize: 11, color: "#475569", letterSpacing: 2, marginBottom: 12 }}>DETECTION ENGINE ALERTS</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {simResult.alerts.map((alert, i) => (
                  <div key={i} style={{
                    background: `${SEV_COLOR[alert.severity] || "#64748b"}11`,
                    border: `1px solid ${SEV_COLOR[alert.severity] || "#64748b"}33`,
                    borderRadius: 8, padding: "12px 16px",
                  }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                      <span style={{ fontWeight: 700, color: SEV_COLOR[alert.severity], fontSize: 13 }}>{alert.title}</span>
                      <div style={{ display: "flex", gap: 8 }}>
                        <span style={{ fontSize: 10, padding: "2px 8px", borderRadius: 20, background: "#1e2d45", color: "#94a3b8" }}>{alert.type}</span>
                        <span style={{ fontSize: 10, padding: "2px 8px", borderRadius: 20, background: `${SEV_COLOR[alert.severity]}22`, color: SEV_COLOR[alert.severity] }}>{alert.severity}</span>
                      </div>
                    </div>
                    <div style={{ fontSize: 11, color: "#64748b" }}>{alert.description}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
