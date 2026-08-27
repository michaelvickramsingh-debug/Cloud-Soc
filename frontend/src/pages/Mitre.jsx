import { useEffect, useState } from "react";
import { fetchJson } from "../utils/api";

const SEV_COLOR = { Critical: "#ef4444", High: "#f97316", Medium: "#eab308", Low: "#22c55e" };
const SEV_RANK = { Critical: 4, High: 3, Medium: 2, Low: 1 };

// Public MITRE ATT&CK technique names for the IDs this project's
// detection engine and Prowler mapping can emit (see backend
// services/simulation.py and services/prowler.py). Used purely to
// enrich the technique ID with a readable name for the dashboard.
const TECHNIQUE_NAMES = {
  "T1566": "Phishing",
  "T1528": "Steal Application Access Token",
  "T1078.004": "Valid Accounts: Cloud Accounts",
  "T1580": "Cloud Infrastructure Discovery",
  "T1537": "Transfer Data to Cloud Account",
  "T1190": "Exploit Public-Facing Application",
  "T1087.004": "Account Discovery: Cloud Account",
  "T1484.001": "Domain or Tenant Policy Modification",
  "T1562.008": "Impair Defenses: Disable Cloud Logs",
  "T1098.001": "Account Manipulation: Additional Cloud Credentials",
  "T1610": "Deploy Container",
  "T1059.004": "Command and Scripting Interpreter: Unix Shell",
  "T1620": "Reflective Code Loading",
  "T1530": "Data from Cloud Storage Object",
  "T1552.005": "Unsecured Credentials: Cloud Instance Metadata API",
  "T1550.001": "Use Alternate Authentication Material: Application Access Token",
  "T1496": "Resource Hijacking",
  "T1110": "Brute Force",
  "T1552": "Unsecured Credentials",
  "T1485": "Data Destruction",
};

// Mock techniques used only when the backend is unreachable — mirrors
// the shape produced by groupAlertsByTechnique() below.
const MOCK_TECHNIQUES = [
  { id: "T1078.004", name: TECHNIQUE_NAMES["T1078.004"], tactic: "Initial Access", severity: "Critical", occurrences: 4, status: "Open", description: "Cloud Token Theft Detected — stolen credentials used to authenticate as a privileged cloud identity." },
  { id: "T1562.008", name: TECHNIQUE_NAMES["T1562.008"], tactic: "Defense Evasion", severity: "Critical", occurrences: 2, status: "Open", description: "CloudTrail Logging Disabled — audit trail disabled ahead of further malicious activity." },
  { id: "T1098.001", name: TECHNIQUE_NAMES["T1098.001"], tactic: "Persistence", severity: "Critical", occurrences: 1, status: "Resolved", description: "Backdoor Account Created — new IAM identity added with programmatic access." },
  { id: "T1484.001", name: TECHNIQUE_NAMES["T1484.001"], tactic: "Privilege Escalation", severity: "Critical", occurrences: 3, status: "Open", description: "Admin Policy Attached to Role — AdministratorAccess granted to a low-privilege role." },
  { id: "T1610", name: TECHNIQUE_NAMES["T1610"], tactic: "Defense Evasion", severity: "Critical", occurrences: 2, status: "Open", description: "Reverse Shell from Container — outbound shell spawned from an unverified container image." },
  { id: "T1496", name: TECHNIQUE_NAMES["T1496"], tactic: "Impact", severity: "Critical", occurrences: 5, status: "Open", description: "Resource Hijacking — Cryptominer Deployed across multiple compute instances." },
  { id: "T1530", name: TECHNIQUE_NAMES["T1530"], tactic: "Exfiltration", severity: "High", occurrences: 1, status: "Resolved", description: "Abnormal Data Volume Exfiltrated from a cloud storage bucket." },
];

function worseSeverity(a, b) {
  return (SEV_RANK[a] || 0) >= (SEV_RANK[b] || 0) ? a : b;
}

function groupAlertsByTechnique(alerts) {
  const groups = new Map();

  for (const alert of alerts) {
    if (!alert.mitre_technique) continue;
    const existing = groups.get(alert.mitre_technique);

    if (!existing) {
      groups.set(alert.mitre_technique, {
        id: alert.mitre_technique,
        name: TECHNIQUE_NAMES[alert.mitre_technique] || alert.mitre_technique,
        tactic: alert.mitre_tactic || "Unknown",
        severity: alert.severity,
        occurrences: 1,
        status: alert.status === "Open" ? "Open" : "Resolved",
        description: alert.title,
      });
    } else {
      existing.occurrences += 1;
      existing.severity = worseSeverity(existing.severity, alert.severity);
      if (alert.status === "Open") existing.status = "Open";
    }
  }

  return Array.from(groups.values()).sort(
    (a, b) => (SEV_RANK[b.severity] || 0) - (SEV_RANK[a.severity] || 0)
  );
}

export default function Mitre() {
  const [techniques, setTechniques] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [usingMock, setUsingMock] = useState(false);
  const [tacticFilter, setTacticFilter] = useState("All");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchJson("/alerts")
      .then(alerts => {
        if (cancelled) return;
        setTechniques(groupAlertsByTechnique(alerts));
        setUsingMock(false);
      })
      .catch(err => {
        if (cancelled) return;
        setError(err.message);
        setTechniques(MOCK_TECHNIQUES);
        setUsingMock(true);
      })
      .finally(() => { if (!cancelled) setLoading(false); });

    return () => { cancelled = true; };
  }, []);

  const tactics = ["All", ...new Set(techniques.map(t => t.tactic))];
  const filtered = techniques.filter(t => tacticFilter === "All" || t.tactic === tacticFilter);

  const FilterBtn = ({ label, value }) => (
    <button onClick={() => setTacticFilter(value)} style={{
      padding: "6px 14px", borderRadius: 20, border: "none", cursor: "pointer", fontSize: 12,
      background: tacticFilter === value ? "#1a2744" : "#0d1220",
      color: tacticFilter === value ? "#4a90e2" : "#64748b",
    }}>{label}</button>
  );

  return (
    <div>
      <div style={{ marginBottom: 28 }}>
        <div style={{ fontSize: 11, color: "#4a90e2", letterSpacing: 3, marginBottom: 8 }}>ATT&CK COVERAGE</div>
        <h2 style={{ fontSize: 26, fontWeight: 800, color: "#f1f5f9", margin: 0 }}>🧩 MITRE ATT&CK Techniques</h2>
        <p style={{ color: "#64748b", marginTop: 8 }}>
          Techniques detected across simulated and ingested findings, grouped from alert data. Run simulations to populate real technique coverage.
        </p>
      </div>

      {usingMock && (
        <div style={{
          background: "#eab30811", border: "1px solid #eab30844", borderRadius: 8,
          padding: "10px 16px", marginBottom: 20, fontSize: 12, color: "#eab308",
        }}>
          ⚠ Backend unavailable — showing sample MITRE data{error ? ` (${error})` : ""}.
        </div>
      )}

      {loading ? (
        <div style={{ textAlign: "center", padding: 60, color: "#64748b" }}>⏳ Loading MITRE techniques...</div>
      ) : (
        <>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
            <span style={{ fontSize: 11, color: "#475569", alignSelf: "center" }}>TACTIC:</span>
            {tactics.map(v => <FilterBtn key={v} label={v} value={v} />)}
          </div>

          <div style={{ fontSize: 12, color: "#475569", marginBottom: 16 }}>
            Showing {filtered.length} of {techniques.length} techniques
          </div>

          {filtered.length === 0 ? (
            <div style={{ textAlign: "center", padding: 60, color: "#334155" }}>
              <div style={{ fontSize: 32, marginBottom: 12 }}>🧩</div>
              <div style={{ fontSize: 16, fontWeight: 600 }}>No techniques detected yet</div>
              <div style={{ fontSize: 13, marginTop: 8 }}>Run a simulation from any Best Practice page to generate MITRE-mapped alerts.</div>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {filtered.map(t => {
                const color = SEV_COLOR[t.severity] || "#64748b";
                return (
                  <div key={t.id} style={{
                    background: "#0d1220", border: `1px solid ${color}33`,
                    borderRadius: 10, padding: "16px 20px",
                  }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, flexWrap: "wrap" }}>
                      <div style={{ flex: 1, minWidth: 240 }}>
                        <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 6, flexWrap: "wrap" }}>
                          <span style={{ fontSize: 11, padding: "2px 10px", borderRadius: 20, background: "#1a2744", color: "#4a90e2", fontFamily: "monospace", fontWeight: 700 }}>{t.id}</span>
                          <span style={{ fontSize: 10, padding: "2px 10px", borderRadius: 20, background: "#1e2d45", color: "#94a3b8" }}>{t.tactic}</span>
                          <span style={{ fontSize: 10, padding: "2px 10px", borderRadius: 20, background: `${color}22`, color, fontWeight: 700 }}>{t.severity}</span>
                          <span style={{ fontSize: 10, padding: "2px 10px", borderRadius: 20, background: t.status === "Open" ? "#ef444422" : "#22c55e22", color: t.status === "Open" ? "#ef4444" : "#22c55e" }}>{t.status}</span>
                        </div>
                        <div style={{ fontSize: 15, fontWeight: 700, color: "#e2e8f0", marginBottom: 6 }}>{t.name}</div>
                        <div style={{ fontSize: 12, color: "#64748b" }}>{t.description}</div>
                      </div>
                      <div style={{ textAlign: "right", flexShrink: 0 }}>
                        <div style={{ fontSize: 24, fontWeight: 900, color }}>{t.occurrences}</div>
                        <div style={{ fontSize: 10, color: "#475569" }}>Occurrence{t.occurrences === 1 ? "" : "s"}</div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
}
