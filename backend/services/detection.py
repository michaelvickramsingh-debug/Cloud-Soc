"""
services/detection.py
----------------------
The IOA / IOM detection engine.

Why is this separate from simulation.py?
  simulation.py generates logs (the attack).
  detection.py analyses logs and produces alerts (the defence).
  Keeping them separate means you could later plug in a different
  detection engine without touching the simulation logic.

How it works:
  1. For each malicious log, check its action text against all rules
  2. First matching rule wins → creates one Alert
  3. Benign logs are skipped (they should never trigger alerts)

IOA = Indicator of Attack   → runtime behavioural signals
IOM = Indicator of Misconfiguration → posture / config signals
"""

from datetime import datetime
from models.log   import Log
from models.alert import Alert
from utils.logger import get_logger

logger = get_logger(__name__)


# ── IOA RULES ─────────────────────────────────────────────────────────────────
# Each rule: keyword to match in log.action (lowercase) → alert metadata

IOA_RULES = [
    {
        "keyword":  "stolen token",
        "title":    "Cloud Token Theft Detected",
        "severity": "Critical",
        "type":     "IOA",
    },
    {
        "keyword":  "logging disabled",
        "title":    "CloudTrail Logging Disabled",
        "severity": "Critical",
        "type":     "IOA",
    },
    {
        "keyword":  "backdoor",
        "title":    "Backdoor Account Created",
        "severity": "Critical",
        "type":     "IOA",
    },
    {
        "keyword":  "administratoraccess",
        "title":    "Admin Policy Attached to Role",
        "severity": "Critical",
        "type":     "IOA",
    },
    {
        "keyword":  "reverse shell",
        "title":    "Reverse Shell from Container",
        "severity": "Critical",
        "type":     "IOA",
    },
    {
        "keyword":  "in-memory payload",
        "title":    "Fileless Malware Execution",
        "severity": "Critical",
        "type":     "IOA",
    },
    {
        "keyword":  "unusual region",
        "title":    "Login from Unusual Region",
        "severity": "High",
        "type":     "IOA",
    },
    {
        "keyword":  "pivot",
        "title":    "Cross-Cloud Lateral Movement",
        "severity": "Critical",
        "type":     "IOA",
    },
    {
        "keyword":  "45 gb",
        "title":    "Abnormal Data Volume Exfiltrated",
        "severity": "Critical",
        "type":     "IOA",
    },
    {
        "keyword":  "mfa challenge bypassed",
        "title":    "MFA Bypass Detected",
        "severity": "Critical",
        "type":     "IOA",
    },
    {
        "keyword":  "malware execution",
        "title":    "Malware Execution on Endpoint",
        "severity": "High",
        "type":     "IOA",
    },
    {
        "keyword":  "credential dumping",
        "title":    "Credential Dumping Detected",
        "severity": "Critical",
        "type":     "IOA",
    },
    {
        "keyword":  "curl | bash",
        "title":    "Suspicious Pipe Execution in Container",
        "severity": "Critical",
        "type":     "IOA",
    },
    {
        "keyword":  "cryptomining",
        "title":    "Resource Hijacking — Cryptominer Deployed",
        "severity": "Critical",
        "type":     "IOA",
    },
    {
        "keyword":  "unauthenticated access",
        "title":    "Unauthenticated API Access Detected",
        "severity": "High",
        "type":     "IOA",
    },
    {
        "keyword":  "federated trust",
        "title":    "Cross-Cloud Federated Token Abuse",
        "severity": "Critical",
        "type":     "IOA",
    },
]

# ── IOM RULES ─────────────────────────────────────────────────────────────────
# Misconfigurations that enabled the attack

IOM_RULES = [
    {
        "keyword":  "unverified external registry",
        "title":    "Container from Unverified Registry",
        "severity": "Medium",
        "type":     "IOM",
    },
    {
        "keyword":  "environment variables",
        "title":    "Secrets Exposed in Environment Variables",
        "severity": "High",
        "type":     "IOM",
    },
    {
        "keyword":  "unauthenticated",
        "title":    "Unauthenticated Endpoint Exposed",
        "severity": "High",
        "type":     "IOM",
    },
]

ALL_RULES = IOA_RULES + IOM_RULES


# ── MAIN FUNCTION ─────────────────────────────────────────────────────────────

def detect(logs: list[Log], scenario_id: int) -> list[Alert]:
    """
    Run all IOA and IOM rules against a list of Log objects.

    Args:
        logs        : list of Log objects from the simulation
        scenario_id : used to set best_practice on each alert

    Returns:
        List of Alert objects — one per matched log (first rule wins)

    Logic:
        - Benign logs (is_malicious=0) are skipped entirely
        - For each malicious log, we check every rule in order
        - The FIRST matching rule creates one alert and we move on
        - related_log_id is set by the caller (simulation.py) after DB insert
    """
    alerts = []
    skipped_benign = 0

    for log in logs:
        # Skip benign logs — they should never generate alerts
        if log.is_malicious == 0:
            skipped_benign += 1
            continue

        action_lower = log.action.lower()
        matched      = False

        for rule in ALL_RULES:
            if rule["keyword"] in action_lower:
                alert = Alert(
                    type            = rule["type"],
                    severity        = rule["severity"],
                    title           = rule["title"],
                    description     = _build_description(log),
                    timestamp       = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                    status          = "Open",
                    best_practice   = scenario_id,
                    mitre_technique = log.mitre_technique,
                    mitre_tactic    = log.mitre_tactic,
                    # related_log_id filled in by simulation.py after DB insert
                )
                alerts.append(alert)
                matched = True
                break   # one alert per log

        if not matched:
            logger.debug("No rule matched for malicious log: %s", log.action[:60])

    logger.info(
        "Detection complete — %d logs → %d alerts (%d benign skipped)",
        len(logs), len(alerts), skipped_benign
    )
    return alerts


# ── PRIVATE ───────────────────────────────────────────────────────────────────

def _build_description(log: Log) -> str:
    """
    Build a human-readable alert description from a log.
    This is what the SOC analyst reads in the alert dashboard.
    """
    return (
        f"Triggered by: {log.action} | "
        f"User: {log.user} | "
        f"Service: {log.cloud_service} | "
        f"Region: {log.region} | "
        f"Source IP: {log.source_ip}"
    )


def detect_threat_from_log(log_dict: dict) -> tuple:
    """
    Detect threats from a CloudTrail log dictionary
    Returns: (severity, reasons_list)
    """
    severity_levels = {'Critical': 3, 'High': 2, 'Medium': 1, 'Low': 0}
    max_severity = None
    reasons = []

    action = log_dict.get('event', '').lower()

    for rule in ALL_RULES:
        if rule['keyword'] in action:
            reasons.append(rule['title'])

            rule_severity = rule['severity']
            if max_severity is None or severity_levels[rule_severity] > severity_levels[max_severity]:
                max_severity = rule_severity

    return max_severity, reasons