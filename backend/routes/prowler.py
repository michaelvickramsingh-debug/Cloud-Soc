

import json
import os
from datetime import datetime
from models.alert    import Alert
from database.database import get_db
from utils.logger    import get_logger
from utils.helpers   import now_str
from config          import Config

logger = get_logger(__name__)

# ── DEFAULT FILE PATH ──────────────────────────────────────────────────────────
# Prowler drops its output here when you run:
#   prowler aws -M json-ocsf -o backend/data/
PROWLER_OUTPUT_PATH = os.path.join(
    os.path.dirname(__file__),   # services/
    "..",                         # backend/
    "data",
    "prowler_output.json"
)

# ── SEVERITY MAPPING ──────────────────────────────────────────────────────────
# Prowler uses: critical, high, medium, low, informational
# CloudGuard uses: Critical, High, Medium, Low
# Map Prowler → CloudGuard format

SEVERITY_MAP = {
    "critical":      "Critical",
    "high":          "High",
    "medium":        "Medium",
    "low":           "Low",
    "informational": "Low",
}

# ── MITRE TECHNIQUE MAP ───────────────────────────────────────────────────────
# Map known Prowler check IDs → MITRE ATT&CK technique IDs
# These are the most common checks that directly relate to cloud attack techniques

MITRE_MAP = {
    # IAM / Identity misconfigurations
    "iam_root_mfa_enabled":                    ("T1078.004", "Initial Access"),
    "iam_user_mfa_enabled_console":            ("T1078.004", "Initial Access"),
    "iam_password_policy_minimum_length_14":   ("T1110",     "Credential Access"),
    "iam_policy_no_administrative_privileges": ("T1484.001", "Privilege Escalation"),
    "iam_root_no_access_key":                  ("T1552",     "Credential Access"),
    "iam_user_no_setup_initial_access_key":    ("T1528",     "Credential Access"),

    # CloudTrail / Logging misconfigurations
    "cloudtrail_multi_region_enabled":         ("T1562.008", "Defense Evasion"),
    "cloudtrail_s3_dataevents_read_enabled":   ("T1562.008", "Defense Evasion"),
    "cloudtrail_log_file_validation_enabled":  ("T1562.008", "Defense Evasion"),
    "cloudtrail_cloudwatch_logging_enabled":   ("T1562.008", "Defense Evasion"),

    # S3 misconfigurations
    "s3_bucket_public_access":                 ("T1530",     "Exfiltration"),
    "s3_bucket_no_public_acl":                 ("T1530",     "Exfiltration"),
    "s3_bucket_default_encryption":            ("T1530",     "Exfiltration"),
    "s3_bucket_versioning_enabled":            ("T1485",     "Impact"),

    # GuardDuty / Detection misconfigurations
    "guardduty_is_enabled":                    ("T1562",     "Defense Evasion"),
    "guardduty_no_high_severity_findings":     ("T1562",     "Defense Evasion"),

    # EC2 / Network misconfigurations
    "ec2_securitygroup_allow_ingress_from_internet_to_ssh_port_22":  ("T1190", "Initial Access"),
    "ec2_securitygroup_allow_ingress_from_internet_to_rdp_port_3389":("T1190", "Initial Access"),
    "ec2_instance_imdsv2_enabled":             ("T1552.005", "Credential Access"),

    # Config / Monitoring
    "config_recorder_all_regions_enabled":     ("T1562",     "Defense Evasion"),
    "securityhub_enabled":                     ("T1562",     "Defense Evasion"),
}


# ── MAIN INGEST FUNCTION ──────────────────────────────────────────────────────

def ingest_prowler_findings(file_path: str = None) -> dict:
    """
    Read a Prowler JSON-OCSF output file and save FAIL findings
    as IOM alerts in the CloudGuard database.

    Args:
        file_path: Path to the Prowler output JSON file.
                   Defaults to backend/data/prowler_output.json

    Returns:
        dict with keys:
          total_findings  : total findings in the file
          fail_count      : number of FAIL findings
          ingested        : number of alerts saved to DB
          skipped         : pass/informational findings skipped
          by_severity     : breakdown of ingested alerts by severity
          errors          : any parsing errors encountered
    """
    path = file_path or PROWLER_OUTPUT_PATH

    # ── Read and parse the file ────────────────────────────────────────
    logger.info("Reading Prowler output from: %s", path)

    if not os.path.exists(path):
        logger.error("Prowler output file not found at: %s", path)
        return {
            "error": (
                f"Prowler output file not found at {path}. "
                "Run: prowler aws -M json-ocsf -o backend/data/ "
                "then rename the output to prowler_output.json"
            )
        }

    try:
        with open(path, "r") as f:
            raw = f.read().strip()

        # Prowler v4 sometimes writes malformed JSON with extra ] characters
        # We handle this by cleaning the raw content before parsing
        findings = _safe_parse_json(raw)

    except Exception as e:
        logger.error("Failed to read Prowler file: %s", str(e))
        return {"error": f"Could not read file: {str(e)}"}

    if not isinstance(findings, list):
        return {"error": "Expected a JSON array of findings. Check your Prowler output format."}

    logger.info("Loaded %d Prowler findings", len(findings))

    # ── Process findings ───────────────────────────────────────────────
    conn       = get_db()
    c          = conn.cursor()
    ingested   = 0
    skipped    = 0
    errors     = []
    by_severity = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}

    for i, finding in enumerate(findings):
        try:
            # Only ingest FAIL findings — PASS findings are not alerts
            status_code = finding.get("status_code", "").upper()
            if status_code != "FAIL":
                skipped += 1
                continue

            alert = _finding_to_alert(finding)
            if alert is None:
                skipped += 1
                continue

            # Save to DB
            c.execute(
                """INSERT INTO alerts
                   (type, severity, title, description, timestamp,
                    status, best_practice, mitre_technique, mitre_tactic)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    alert.type,       alert.severity,  alert.title,
                    alert.description,alert.timestamp, alert.status,
                    alert.best_practice,
                    alert.mitre_technique, alert.mitre_tactic,
                )
            )

            by_severity[alert.severity] = by_severity.get(alert.severity, 0) + 1
            ingested += 1

        except Exception as e:
            errors.append(f"Finding {i}: {str(e)}")
            logger.warning("Error processing finding %d: %s", i, str(e))

    conn.commit()
    conn.close()

    logger.info(
        "Prowler ingestion complete — %d ingested, %d skipped, %d errors",
        ingested, skipped, len(errors)
    )

    return {
        "total_findings": len(findings),
        "fail_count":     ingested + len(errors),
        "ingested":       ingested,
        "skipped":        skipped,
        "by_severity":    by_severity,
        "errors":         errors,
    }


def get_prowler_summary() -> dict:
    """
    Return a summary of all Prowler-sourced IOM alerts in the database.
    Used by GET /api/prowler/summary

    Returns breakdown by severity and status so the frontend
    can show a Prowler posture panel separate from simulated IOA alerts.
    """
    conn = get_db()
    c    = conn.cursor()

    total = c.execute(
        "SELECT COUNT(*) FROM alerts WHERE type='IOM'"
    ).fetchone()[0]

    by_severity = c.execute(
        """SELECT severity, COUNT(*) as count
           FROM alerts WHERE type='IOM'
           GROUP BY severity ORDER BY count DESC"""
    ).fetchall()

    by_status = c.execute(
        """SELECT status, COUNT(*) as count
           FROM alerts WHERE type='IOM'
           GROUP BY status"""
    ).fetchall()

    recent = c.execute(
        """SELECT title, severity, timestamp, mitre_technique
           FROM alerts WHERE type='IOM'
           ORDER BY timestamp DESC LIMIT 5"""
    ).fetchall()

    conn.close()

    return {
        "total_iom_alerts":  total,
        "by_severity":       [dict(r) for r in by_severity],
        "by_status":         [dict(r) for r in by_status],
        "recent_findings":   [dict(r) for r in recent],
    }


# ── PRIVATE HELPERS ───────────────────────────────────────────────────────────

def _finding_to_alert(finding: dict):
    """
    Convert one Prowler JSON-OCSF finding dict → Alert object.

    Prowler OCSF finding structure:
      finding_info.title  → what the check is
      finding_info.desc   → why it matters
      severity            → Critical/High/Medium/Low
      status_code         → FAIL / PASS / MANUAL
      status_detail       → specific reason this check failed
      resources[0].name   → which AWS resource failed
      resources[0].cloud.region → which region
      metadata.event_code → check ID for MITRE mapping
      remediation.desc    → how to fix it
      time                → when Prowler ran the check
    """
    # Extract fields safely with fallbacks
    finding_info  = finding.get("finding_info", {})
    resources     = finding.get("resources", [{}])
    resource      = resources[0] if resources else {}
    cloud         = resource.get("cloud", {})
    remediation   = finding.get("remediation", {})
    metadata      = finding.get("metadata", {})

    title         = finding_info.get("title", "Unknown Prowler Finding")
    description   = finding_info.get("desc", "")
    status_detail = finding.get("status_detail", "")
    resource_name = resource.get("name", "unknown-resource")
    region        = cloud.get("region", "unknown-region")
    account       = cloud.get("account", {}).get("uid", "unknown-account")
    remediation_desc = remediation.get("desc", "")
    check_id      = metadata.get("event_code", "")
    timestamp     = finding.get("time", now_str())

    # Map severity
    raw_severity  = finding.get("severity", "medium").lower()
    severity      = SEVERITY_MAP.get(raw_severity, "Medium")

    # Map to MITRE technique
    mitre_technique, mitre_tactic = MITRE_MAP.get(
        check_id, ("", "")
    )

    # Build a rich description the SOC analyst can act on
    description_parts = []
    if status_detail:
        description_parts.append(f"Finding: {status_detail}")
    if description:
        description_parts.append(f"Context: {description}")
    description_parts.append(f"Resource: {resource_name}")
    description_parts.append(f"Region: {region}")
    description_parts.append(f"Account: {account}")
    if remediation_desc:
        description_parts.append(f"Remediation: {remediation_desc}")
    if check_id:
        description_parts.append(f"Check ID: {check_id}")

    full_description = " | ".join(description_parts)

    # Validate we have a usable title
    if not title or title == "Unknown Prowler Finding":
        logger.debug("Skipping finding with no title: %s", check_id)
        return None

    return Alert(
        type             = "IOM",
        severity         = severity,
        title            = title[:200],          # cap length for DB
        description      = full_description[:1000],
        timestamp        = timestamp,
        status           = "Open",
        best_practice    = 0,                    # Prowler findings link to posture, not a specific BP
        mitre_technique  = mitre_technique,
        mitre_tactic     = mitre_tactic,
    )


def _safe_parse_json(raw: str) -> list:
    """
    Safely parse Prowler JSON output.

    Prowler v4 has a known bug where it sometimes writes ] instead of ,
    between findings, producing invalid JSON. This function handles that
    by trying standard parse first, then falling back to line-by-line.

    Reference: https://github.com/prowler-cloud/prowler/issues/3675
    """
    # Try standard JSON parse first
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Fallback: try to fix the common Prowler malformed JSON bug
    logger.warning("Standard JSON parse failed — attempting repair of Prowler output")
    try:
        # Replace the known bad pattern: ] followed by { with , {
        import re
        fixed = re.sub(r'\]\s*\{', ', {', raw)
        # Ensure it's wrapped in an array
        if not fixed.strip().startswith('['):
            fixed = '[' + fixed + ']'
        return json.loads(fixed)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Could not parse Prowler output even after repair attempt: {str(e)}. "
            "Try running Prowler again with: prowler aws -M json-ocsf"
        )