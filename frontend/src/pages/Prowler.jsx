import { useEffect, useState } from "react";
import { fetchJson } from "../utils/api";

const SEV_COLOR = { Critical: "#ef4444", High: "#f97316", Medium: "#eab308", Low: "#22c55e" };

// Mock findings used only when the backend is unreachable — mirrors the
// shape produced by mapAlertsToFindings() below.
const MOCK_FINDINGS = [
  { id: "iam_root_mfa_enabled", severity: "Critical", status: "Open", resource: "root-account", region: "global", description: "MFA is not enabled for the root account.", remediation: "Enable a hardware or virtual MFA device for the root account immediately." },
  { id: "s3_bucket_public_access", severity: "Critical", status: "Open", resource: "customer-data-backup", region: "us-east-1", description: "S3 bucket allows public read access.", remediation: "Enable S3 Block Public Access and review the bucket policy for public grants." },
  { id: "ec2_securitygroup_allow_ingress_from_internet_to_ssh_port_22", severity: "High", status: "Open", resource: "sg-0a1b2c3d4e5f", region: "us-east-1", description: "Security group allows unrestricted SSH access (0.0.0.0/0 on port 22).", remediation: "Restrict inbound SSH to known IP ranges or use a bastion/SSM Session Manager." },
  { id: "cloudtrail_multi_region_enabled", severity: "Medium", status: "Resolved", resource: "trail-main", region: "us-east-1", description: "CloudTrail is not enabled across all regions.", remediation: "Enable a multi-region trail so activity in every region is logged." },
  { id: "guardduty_is_enabled", severity: "High", status: "Open", resource: "account-533267", region: "eu-west-1", description: "GuardDuty is not enabled in this region.", remediation: "Enable GuardDuty in all active regions to detect threats and anomalous activity." },
  { id: "iam_password_policy_minimum_length_14", severity: "Low", status: "Resolved", resource: "account-password-policy", region: "global", description: "IAM password policy allows passwords shorter than 14 characters.", remediation: "Update the account password policy to require a minimum length of 14 characters." },
];

const MOCK_SUMMARY = {
  total_iom_alerts: MOCK_FINDINGS.length,
  by_severity: [
    { severity: "Critical", count: 2 },
    { severity: "High", count: 2 },
    { severity: "Medium", count: 1 },
    { severity: "Low", count: 1 },
  ],
  by_status: [
    { status: "Open", count: 4 },
    { status: "Resolved", count: 2 },
  ],
};

// Alert descriptions are built as " | "-joined "Key: value" segments by
// backend/services/prowler.py and services/detection.py. Parse them back
// out so the table can show dedicated Resource/Region/Remediation columns
// without the backend needing new fields.
function parseDescription(description) {
  const parts = { resource: "—", region: "—", remediation: "", summary: description };
  if (!description) return parts;

  const segments = description.split(" | ");
  const summaryPieces = [];

  for (const segment of segments) {
    const idx = segment.indexOf(": ");
    if (idx === -1) { summaryPieces.push(segment); continue; }
    const key = segment.slice(0, idx).trim().toLowerCase();
    const value = segment.slice(idx + 2).trim();

    if (key === "resource" || key === "triggered by") parts.resource = value;
    else if (key === "region") parts.region = value;
    else if (key === "remediation") parts.remediation = value;
    else if (key === "finding" || key === "context") summaryPieces.push(value);
  }

  if (summaryPieces.length) parts.summary = summaryPieces.join(" — ");
  return parts;
}

function mapAlertsToFindings(alerts) {
  return alerts
    .filter(a => a.type === "IOM")
    .map(a => {
      const parsed = parseDescription(a.description);
      return {
        id: a.id,
        severity: a.severity,
        status: a.status,
        resource: parsed.resource,
        region: parsed.region,
        description: a.title,
        remediation: parsed.remediation || "No remediation details available for this finding.",
        summary: parsed.summary,
      };
    });
}

export default function Prowler() {
  const [findings, setFindings] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [usingMock, setUsingMock] = useState(false);
  const [severityFilter, setSeverityFilter] = useState("All");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    Promise.all([fetchJson("/prowler/summary"), fetchJson("/alerts")])
      .then(([summaryData, alerts]) => {
        if (cancelled) return;
        setSummary(summaryData);
        setFindings(mapAlertsToFindings(alerts));
        setUsingMock(false);
      })
      .catch(err => {
        if (cancelled) return;
        setError(err.message);
        setSummary(MOCK_SUMMARY);
        setFindings(MOCK_FINDINGS);
        setUsingMock(true);
      })
      .finally(() => { if (!cancelled) setLoading(false); });

    return () => { cancelled = true; };
  }, []);

  const filtered = findings.filter(f => severityFilter === "All" || f.severity === severityFilter);

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
        <div style={{ fontSize: 11, color: "#4a90e2", letterSpacing: 3, marginBottom: 8 }}>CLOUD SECURITY POSTURE</div>
        <h2 style={{ fontSize: 26, fontWeight: 800, color: "#f1f5f9", margin: 0 }}>☂️ Prowler Findings</h2>
        <p style={{ color: "#64748b", marginTop: 8 }}>
          Misconfiguration findings from Prowler CSPM scans and the detection engine. Run <code>POST /api/prowler/ingest</code> against a real Prowler output file to populate this with live AWS posture data.
        </p>
      </div>

      {usingMock && (
        <div style={{
          background: "#eab30811", border: "1px solid #eab30844", borderRadius: 8,
          padding: "10px 16px", marginBottom: 20, fontSize: 12, color: "#eab308",
        }}>
          ⚠ Backend unavailable — showing sample Prowler findings{error ? ` (${error})` : ""}.
        </div>
      )}

      {loading ? (
        <div style={{ textAlign: "center", padding: 60, color: "#64748b" }}>⏳ Loading Prowler findings...</div>
      ) : (
        <>
          {summary && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16, marginBottom: 28 }}>
              <div style={{ background: "#0d1220", border: "1px solid #1e2d45", borderRadius: 10, padding: "20px 24px" }}>
                <div style={{ fontSize: 32, fontWeight: 800, color: "#4a90e2" }}>{summary.total_iom_alerts}</div>
                <div style={{ fontSize: 12, color: "#64748b" }}>Total IOM Findings</div>
              </div>
              <div style={{ background: "#0d1220", border: "1px solid #1e2d45", borderRadius: 10, padding: "20px 24px" }}>
                <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                  {summary.by_severity.map(s => (
                    <span key={s.severity} style={{ fontSize: 12, color: SEV_COLOR[s.severity] || "#64748b", fontWeight: 700 }}>
                      {s.severity}: {s.count}
                    </span>
                  ))}
                </div>
                <div style={{ fontSize: 12, color: "#64748b", marginTop: 8 }}>By Severity</div>
              </div>
              <div style={{ background: "#0d1220", border: "1px solid #1e2d45", borderRadius: 10, padding: "20px 24px" }}>
                <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                  {summary.by_status.map(s => (
                    <span key={s.status} style={{ fontSize: 12, color: s.status === "Open" ? "#ef4444" : "#22c55e", fontWeight: 700 }}>
                      {s.status}: {s.count}
                    </span>
                  ))}
                </div>
                <div style={{ fontSize: 12, color: "#64748b", marginTop: 8 }}>By Status</div>
              </div>
            </div>
          )}

          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
            <span style={{ fontSize: 11, color: "#475569", alignSelf: "center" }}>SEVERITY:</span>
            {["All", "Critical", "High", "Medium", "Low"].map(v => <FilterBtn key={v} label={v} value={v} />)}
          </div>

          <div style={{ fontSize: 12, color: "#475569", marginBottom: 16 }}>
            Showing {filtered.length} of {findings.length} findings
          </div>

          {filtered.length === 0 ? (
            <div style={{ textAlign: "center", padding: 60, color: "#334155" }}>
              <div style={{ fontSize: 32, marginBottom: 12 }}>☂️</div>
              <div style={{ fontSize: 16, fontWeight: 600 }}>No Prowler findings yet</div>
              <div style={{ fontSize: 13, marginTop: 8 }}>Ingest a Prowler scan via <code>POST /api/prowler/ingest</code> to populate findings.</div>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {filtered.map(f => {
                const color = SEV_COLOR[f.severity] || "#64748b";
                return (
                  <div key={f.id} style={{
                    background: "#0d1220", border: `1px solid ${color}33`,
                    borderRadius: 10, padding: "16px 20px",
                  }}>
                    <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 8, flexWrap: "wrap" }}>
                      <span style={{ fontSize: 11, padding: "2px 10px", borderRadius: 20, background: "#1a2744", color: "#4a90e2", fontFamily: "monospace" }}>{f.id}</span>
                      <span style={{ fontSize: 10, padding: "2px 10px", borderRadius: 20, background: `${color}22`, color, fontWeight: 700 }}>{f.severity}</span>
                      <span style={{ fontSize: 10, padding: "2px 10px", borderRadius: 20, background: f.status === "Open" ? "#ef444422" : "#22c55e22", color: f.status === "Open" ? "#ef4444" : "#22c55e" }}>{f.status}</span>
                      <span style={{ fontSize: 10, padding: "2px 10px", borderRadius: 20, background: "#1e2d45", color: "#94a3b8" }}>📍 {f.region}</span>
                      <span style={{ fontSize: 10, padding: "2px 10px", borderRadius: 20, background: "#1e2d45", color: "#94a3b8" }}>🧱 {f.resource}</span>
                    </div>
                    <div style={{ fontSize: 15, fontWeight: 700, color: "#e2e8f0", marginBottom: 6 }}>{f.description}</div>
                    {f.summary && f.summary !== f.description && (
                      <div style={{ fontSize: 12, color: "#64748b", marginBottom: 8 }}>{f.summary}</div>
                    )}
                    <div style={{
                      fontSize: 12, color: "#22c55e", background: "#22c55e11",
                      border: "1px solid #22c55e33", borderRadius: 6, padding: "8px 12px",
                    }}>
                      💡 {f.remediation}
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
