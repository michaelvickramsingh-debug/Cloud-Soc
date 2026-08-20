import { useEffect, useState } from "react";

const API = "http://localhost:5000/api";

const SEV_COLOR = { Critical: "#ef4444", High: "#f97316", Medium: "#eab308", Low: "#22c55e" };
const BP_COLOR = { 1: "#4a90e2", 2: "#06b6d4", 3: "#10b981", 4: "#8b5cf6", 5: "#f59e0b" };
const BP_ICON = { 1: "🧠", 2: "🔗", 3: "🛡️", 4: "👥", 5: "⚙️" };

// There is no /api/practices endpoint on the backend yet, so this static
// guide content is the only source for these descriptions today. Kept as a
// fallback (rather than the sole source) so a future /api/practices route
// can override it without any frontend changes.
const FALLBACK_PRACTICES = [
  {
    id: 1,
    title: "Threat Intelligence",
    summary: "Correlate cloud activity against known adversary tradecraft instead of reacting to isolated alerts.",
    key_insight: "Attackers reuse the same cloud-specific techniques across campaigns — recognizing the pattern early cuts detection time dramatically.",
    what_without: "Analysts see a stream of disconnected, low-context alerts and can't tell a real intrusion from noise until damage is already done.",
    what_with: "Alerts are enriched with adversary context, so the SOC recognizes a known attack pattern in progress and responds before it escalates.",
  },
  {
    id: 2,
    title: "Control Plane Context",
    summary: "Understand identity, permissions, and configuration changes — the cloud control plane is the new perimeter.",
    key_insight: "Most cloud breaches involve control-plane misuse (IAM, roles, policies) rather than traditional malware on a host.",
    what_without: "A privilege escalation via a misconfigured IAM policy looks like routine admin activity and goes unnoticed for days or weeks.",
    what_with: "Every permission and policy change is tracked with context, so an unauthorized privilege escalation is flagged the moment it happens.",
  },
  {
    id: 3,
    title: "Runtime Protection",
    summary: "Monitor workloads (containers, serverless, VMs) as they execute, not just their static configuration.",
    key_insight: "Fileless and in-memory techniques evade traditional scanning because there's no file ever written to disk.",
    what_without: "A reverse shell spawned inside a container runs silently — nothing on disk ever gets scanned, so nothing gets caught.",
    what_with: "Runtime behavior is monitored directly, so anomalous process activity inside a container or function is caught as it happens.",
  },
  {
    id: 4,
    title: "Cloud Expertise",
    summary: "Cloud-native attacks require analysts fluent in cloud services, not just traditional network/endpoint security.",
    key_insight: "A login from an unusual region or an unfamiliar API call pattern only looks suspicious to someone who knows what 'normal' looks like for that cloud environment.",
    what_without: "An analyst without cloud-specific training dismisses an impossible-travel login alert as a false positive.",
    what_with: "Cloud-fluent analysts recognize subtle deviations from normal cloud usage and investigate them before they become a breach.",
  },
  {
    id: 5,
    title: "Automate Response",
    summary: "Machine-speed attacks need machine-speed containment — manual response can't keep pace in the cloud.",
    key_insight: "Cloud resources (compute, storage, credentials) can be created, escalated, and abused within minutes, far faster than a human-driven response process.",
    what_without: "By the time an analyst manually revokes a compromised credential, the attacker has already pivoted to other resources.",
    what_with: "Automated playbooks isolate compromised resources and revoke credentials within seconds of detection, containing the blast radius.",
  },
];

export default function BestPractice({ id }) {
  const [practice, setPractice] = useState(null);
  const [loading, setLoading] = useState(true);
  const [usingFallback, setUsingFallback] = useState(false);
  const [simResult, setSimResult] = useState(null);
  const [simLoading, setSimLoading] = useState(false);
  const [step, setStep] = useState("idle"); // idle | running | done

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    fetch(`${API}/practices`)
      .then(r => {
        if (!r.ok) throw new Error(`Request failed with status ${r.status}`);
        return r.json();
      })
      .then(data => {
        if (cancelled) return;
        setPractice(data.find(p => p.id === id));
        setUsingFallback(false);
      })
      .catch(() => {
        if (cancelled) return;
        setPractice(FALLBACK_PRACTICES.find(p => p.id === id));
        setUsingFallback(true);
      })
      .finally(() => { if (!cancelled) setLoading(false); });

    setSimResult(null);
    setStep("idle");
    return () => { cancelled = true; };
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

  if (loading) return <div style={{ textAlign: "center", padding: 60, color: "#64748b" }}>⏳ Loading best practice...</div>;
  if (!practice) return <div style={{ color: "#64748b", padding: 40 }}>Practice not found.</div>;

  const color = BP_COLOR[id];

  return (
    <div>
      {usingFallback && (
        <div style={{
          background: "#eab30811", border: "1px solid #eab30844", borderRadius: 8,
          padding: "10px 16px", marginBottom: 20, fontSize: 12, color: "#eab308",
        }}>
          ⚠ Backend unavailable — showing built-in guide content (attack simulation below still requires the backend).
        </div>
      )}

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
