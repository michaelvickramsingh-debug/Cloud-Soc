import { useEffect, useState } from "react";
import { fetchJson } from "../utils/api";

const SEV_COLOR = { Critical: "#ef4444", High: "#f97316", Medium: "#eab308", Low: "#22c55e", Info: "#64748b" };

// Mock events used only when the backend is unreachable — mirrors the
// shape returned by mapLogsToEvents() so real data can drop in later.
const MOCK_EVENTS = [
  { id: "m1", timestamp: "2026-08-20T09:42:11Z", eventType: "Credential Access", severity: "Critical", source: "AWS IAM · us-east-1", description: "Stolen access token used to authenticate as root from an unrecognized device", isMalicious: true },
  { id: "m2", timestamp: "2026-08-20T09:41:03Z", eventType: "Defense Evasion", severity: "Critical", source: "AWS CloudTrail · us-east-1", description: "CloudTrail logging disabled shortly before suspicious API activity", isMalicious: true },
  { id: "m3", timestamp: "2026-08-20T09:38:47Z", eventType: "Persistence", severity: "Critical", source: "AWS IAM · eu-west-1", description: "Backdoor IAM account created with programmatic access", isMalicious: true },
  { id: "m4", timestamp: "2026-08-20T09:35:20Z", eventType: "Privilege Escalation", severity: "Critical", source: "AWS IAM · eu-west-1", description: "AdministratorAccess policy attached to a low-privilege role", isMalicious: true },
  { id: "m5", timestamp: "2026-08-20T09:30:05Z", eventType: "Initial Access", severity: "High", source: "Azure AD · West Europe", description: "Login from an unusual region flagged by impossible-travel detection", isMalicious: true },
  { id: "m6", timestamp: "2026-08-20T09:26:41Z", eventType: "Execution", severity: "Critical", source: "GKE Cluster · us-central1", description: "Reverse shell spawned from a container running an unverified image", isMalicious: true },
  { id: "m7", timestamp: "2026-08-20T09:20:18Z", eventType: "Impact", severity: "Critical", source: "AWS EC2 · ap-southeast-1", description: "Cryptomining process deployed across multiple compute instances", isMalicious: true },
  { id: "m8", timestamp: "2026-08-20T09:12:54Z", eventType: "Exfiltration", severity: "Critical", source: "AWS S3 · us-east-1", description: "45 GB of data exfiltrated from a customer records bucket", isMalicious: true },
  { id: "m9", timestamp: "2026-08-20T09:05:32Z", eventType: "Benign Activity", severity: "Info", source: "AWS IAM · us-east-1", description: "User alice@corp.com listed S3 buckets — routine console activity", isMalicious: false },
  { id: "m10", timestamp: "2026-08-20T08:58:09Z", eventType: "Benign Activity", severity: "Info", source: "GCP Compute · us-central1", description: "Scheduled instance health check completed successfully", isMalicious: false },
];

function mapLogsToEvents(logs) {
  // /api/logs (routes/logs.py) normalizes both simulated and live rows to
  // { id, timestamp, user, event, ip, region, source, severity, type }.
  // It never returns action, cloud_service, is_malicious, or mitre_tactic —
  // referencing those left every row showing "undefined — by unknown" and
  // stuck on the Info/Benign fallback regardless of actual severity.
  return logs.map(l => {
    const severity = l.severity || "Info";
    return {
      id: l.id,
      timestamp: l.timestamp,
      eventType: l.type === "simulated" ? "Simulated Attack" : "Live CloudTrail Activity",
      severity,
      source: [l.source, l.region].filter(Boolean).join(" · ") || l.user || "Unknown source",
      description: l.event
        ? (l.user ? `${l.event} — by ${l.user}` : l.event)
        : "Unknown event",
      isMalicious: ["Critical", "High"].includes(severity),
    };
  });
}

export default function Timeline() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [usingMock, setUsingMock] = useState(false);
  const [severityFilter, setSeverityFilter] = useState("All");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchJson("/logs")
      .then(logs => {
        if (cancelled) return;
        setEvents(mapLogsToEvents(logs));
        setUsingMock(false);
      })
      .catch(err => {
        if (cancelled) return;
        setError(err.message);
        setEvents(MOCK_EVENTS);
        setUsingMock(true);
      })
      .finally(() => { if (!cancelled) setLoading(false); });

    return () => { cancelled = true; };
  }, []);

  const filtered = events.filter(e => severityFilter === "All" || e.severity === severityFilter);

  const FilterBtn = ({ label, value }) => (
    <button onClick={() => setSeverityFilter(value)} style={{
      padding: "6px 14px", borderRadius: 20, border: "none", cursor: "pointer", fontSize: 12,
      background: severityFilter === value ? "#1a2744" : "#0d1220",
      color: severityFilter === value ? "#4a90e2" : "#64748b",
    }}>{label}</button>
  );

  return (
    <div>
      <div style={{ marginBottom: 28 }}>
        <div style={{ fontSize: 11, color: "#4a90e2", letterSpacing: 3, marginBottom: 8 }}>CHRONOLOGICAL VIEW</div>
        <h2 style={{ fontSize: 26, fontWeight: 800, color: "#f1f5f9", margin: 0 }}>🕒 Event Timeline</h2>
        <p style={{ color: "#64748b", marginTop: 8 }}>
          Cloud activity and detection events in chronological order — newest first. Run simulations from any Best Practice page to populate real events.
        </p>
      </div>

      {usingMock && (
        <div style={{
          background: "#eab30811", border: "1px solid #eab30844", borderRadius: 8,
          padding: "10px 16px", marginBottom: 20, fontSize: 12, color: "#eab308",
        }}>
          ⚠ Backend unavailable — showing sample timeline data{error ? ` (${error})` : ""}.
        </div>
      )}

      {loading ? (
        <div style={{ textAlign: "center", padding: 60, color: "#64748b" }}>⏳ Loading timeline events...</div>
      ) : (
        <>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
            <span style={{ fontSize: 11, color: "#475569", alignSelf: "center" }}>SEVERITY:</span>
            {["All", "Critical", "High", "Medium", "Low", "Info"].map(v => <FilterBtn key={v} label={v} value={v} />)}
          </div>

          <div style={{ fontSize: 12, color: "#475569", marginBottom: 16 }}>
            Showing {filtered.length} of {events.length} events
          </div>

          {filtered.length === 0 ? (
            <div style={{ textAlign: "center", padding: 60, color: "#334155" }}>
              <div style={{ fontSize: 32, marginBottom: 12 }}>🕒</div>
              <div style={{ fontSize: 16, fontWeight: 600 }}>No events yet</div>
              <div style={{ fontSize: 13, marginTop: 8 }}>Run a simulation from any Best Practice page to generate timeline events.</div>
            </div>
          ) : (
            <div style={{ position: "relative", paddingLeft: 20 }}>
              <div style={{ position: "absolute", left: 4, top: 6, bottom: 6, width: 2, background: "#1e2d45" }} />
              <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                {filtered.map(event => {
                  const color = SEV_COLOR[event.severity] || "#64748b";
                  return (
                    <div key={event.id} style={{ position: "relative" }}>
                      <div style={{
                        position: "absolute", left: -20, top: 6, width: 10, height: 10, borderRadius: "50%",
                        background: color, border: "2px solid #0a0e1a",
                      }} />
                      <div style={{
                        background: "#0d1220", border: `1px solid ${color}33`,
                        borderRadius: 10, padding: "14px 18px",
                      }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
                          <div style={{ flex: 1 }}>
                            <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 6, flexWrap: "wrap" }}>
                              <span style={{ fontSize: 11, color: "#334155", fontFamily: "monospace" }}>{event.timestamp}</span>
                              <span style={{ fontSize: 10, padding: "2px 10px", borderRadius: 20, background: "#1e2d45", color: "#94a3b8" }}>{event.eventType}</span>
                              <span style={{ fontSize: 10, padding: "2px 10px", borderRadius: 20, background: `${color}22`, color, fontWeight: 700 }}>{event.severity}</span>
                            </div>
                            <div style={{ fontSize: 13, color: "#e2e8f0", marginBottom: 4 }}>{event.description}</div>
                            <div style={{ fontSize: 11, color: "#475569" }}>{event.source}</div>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
