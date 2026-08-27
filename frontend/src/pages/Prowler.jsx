import { useEffect, useState } from "react";
import { fetchJson } from "../utils/api";

const SEVERITY_COLORS = {
  Critical: "#ef4444",
  High: "#f97316",
  Medium: "#eab308",
  Low: "#22c55e",
};

const SAMPLE_FINDINGS = [
  { id: "iam_root_mfa_enabled", severity: "Critical", status: "Open", resource: "root-account", region: "global", title: "Root account MFA is not enabled", description: "Enable a hardware or virtual MFA device for the root account immediately." },
  { id: "s3_bucket_public_access", severity: "Critical", status: "Open", resource: "customer-data-backup", region: "us-east-1", title: "S3 bucket allows public read access", description: "Enable S3 Block Public Access and review the bucket policy." },
  { id: "guardduty_is_enabled", severity: "High", status: "Open", resource: "account-533267", region: "eu-west-1", title: "GuardDuty is not enabled in this region", description: "Enable GuardDuty in all active regions." },
];

function mapAlert(alert) {
  const fields = { resource: "Unknown resource", region: "Unknown region", remediation: "No remediation details available." };
  for (const segment of (alert.description || "").split(" | ")) {
    const separator = segment.indexOf(": ");
    if (separator === -1) continue;
    const key = segment.slice(0, separator).toLowerCase();
    const value = segment.slice(separator + 2);
    if (key === "resource" || key === "triggered by") fields.resource = value;
    if (key === "region") fields.region = value;
    if (key === "remediation") fields.remediation = value;
  }
  return { ...alert, ...fields, title: alert.title || "Prowler finding" };
}

export default function Prowler() {
  const [findings, setFindings] = useState([]);
  const [summary, setSummary] = useState(null);
  const [filter, setFilter] = useState("All");
  const [loading, setLoading] = useState(true);
  const [usingSample, setUsingSample] = useState(false);

  useEffect(() => {
    Promise.all([fetchJson("/prowler/summary"), fetchJson("/alerts")])
      .then(([summaryData, alerts]) => {
        setSummary(summaryData);
        setFindings(alerts.filter(alert => alert.type === "IOM").map(mapAlert));
      })
      .catch(() => {
        setUsingSample(true);
        setFindings(SAMPLE_FINDINGS);
        setSummary({ total_iom_alerts: SAMPLE_FINDINGS.length });
      })
      .finally(() => setLoading(false));
  }, []);

  const visibleFindings = findings.filter(finding => filter === "All" || finding.severity === filter);

  return (
    <div>
      <div style={{ marginBottom: 28 }}>
        <div style={{ fontSize: 11, color: "#4a90e2", letterSpacing: 3, marginBottom: 8 }}>CLOUD SECURITY POSTURE</div>
        <h2 style={{ fontSize: 26, fontWeight: 800, color: "#f1f5f9", margin: 0 }}>Prowler Findings</h2>
        <p style={{ color: "#64748b", marginTop: 8 }}>Misconfiguration findings from Prowler CSPM scans and the detection engine.</p>
      </div>

      {usingSample && <div style={{ color: "#eab308", background: "#eab30811", border: "1px solid #eab30844", borderRadius: 8, padding: "10px 16px", marginBottom: 20, fontSize: 12 }}>Backend unavailable. Showing sample findings.</div>}
      {loading ? <div style={{ color: "#64748b", padding: 40 }}>Loading Prowler findings...</div> : (
        <>
          <div style={{ display: "flex", gap: 16, marginBottom: 24 }}>
            <div style={{ background: "#0d1220", border: "1px solid #1e2d45", borderRadius: 10, padding: "20px 24px" }}>
              <div style={{ fontSize: 32, fontWeight: 800, color: "#4a90e2" }}>{summary?.total_iom_alerts ?? findings.length}</div>
              <div style={{ fontSize: 12, color: "#64748b" }}>Total IOM Findings</div>
            </div>
          </div>
          <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
            {["All", "Critical", "High", "Medium", "Low"].map(value => <button key={value} onClick={() => setFilter(value)} style={{ padding: "6px 14px", border: 0, borderRadius: 20, cursor: "pointer", background: filter === value ? "#1a2744" : "#0d1220", color: filter === value ? "#4a90e2" : "#64748b" }}>{value}</button>)}
          </div>
          <div style={{ color: "#475569", fontSize: 12, marginBottom: 16 }}>Showing {visibleFindings.length} of {findings.length} findings</div>
          {visibleFindings.length === 0 ? <div style={{ color: "#64748b", padding: 40 }}>No Prowler findings yet. Ingest a scan with `POST /api/prowler/ingest`.</div> : visibleFindings.map(finding => {
            const color = SEVERITY_COLORS[finding.severity] || "#64748b";
            return <div key={finding.id} style={{ background: "#0d1220", border: `1px solid ${color}55`, borderRadius: 10, padding: "16px 20px", marginBottom: 10 }}>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
                <span style={{ color: "#4a90e2", fontFamily: "monospace", fontSize: 11 }}>{finding.id}</span>
                <span style={{ color, fontSize: 11, fontWeight: 700 }}>{finding.severity}</span>
                <span style={{ color: finding.status === "Open" ? "#ef4444" : "#22c55e", fontSize: 11 }}>{finding.status}</span>
                <span style={{ color: "#94a3b8", fontSize: 11 }}>{finding.region} · {finding.resource}</span>
              </div>
              <div style={{ color: "#e2e8f0", fontWeight: 700, marginBottom: 8 }}>{finding.title}</div>
              <div style={{ color: "#22c55e", fontSize: 12 }}>{finding.remediation || finding.description}</div>
            </div>;
          })}
        </>
      )}
    </div>
  );
}
