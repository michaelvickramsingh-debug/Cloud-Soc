"""
services/simulation.py
-----------------------
Generates cloud attack scenarios as realistic Log sequences,
then orchestrates the full simulation pipeline:

    generate logs → mix in benign → stagger timestamps
        → save to DB → run detection → save alerts → return summary

The 5 scenarios map directly to CrowdStrike's CDR best practices
and MITRE ATT&CK for Cloud tactics.
"""

import random
from models.log       import Log
from models.alert     import Alert
from services.detection import detect
from database.database  import get_db
from utils.helpers      import staggered_times, now_str, safe_divide
from utils.logger       import get_logger
from config             import Config

logger = get_logger(__name__)


# ── CONSTANTS ─────────────────────────────────────────────────────────────────

USERS        = ["alice@corp.com", "bob@corp.com", "svc-deploy", "admin@corp.com"]
SAFE_REGIONS = ["us-east-1", "eu-west-1"]

MALICIOUS_IPS = [
    "185.220.101.45",   # known Tor exit node
    "45.33.32.156",     # known C2 server
    "92.118.160.10",    # attacker infrastructure
    "198.98.51.189",    # malicious ASN
]
INTERNAL_IPS = ["10.0.0.1", "10.0.1.42", "192.168.1.10", "172.16.0.5"]


# ── BENIGN LOG GENERATOR ──────────────────────────────────────────────────────

_BENIGN_ACTIONS = [
    ("ListBuckets",              "AWS S3",         "Low"),
    ("GetObject",                "AWS S3",         "Low"),
    ("DescribeInstances",        "AWS EC2",        "Low"),
    ("GetCallerIdentity",        "AWS IAM",        "Low"),
    ("ListRoles",                "AWS IAM",        "Low"),
    ("PutObject",                "AWS S3",         "Low"),
    ("StartInstances",           "AWS EC2",        "Low"),
    ("DescribeSecurityGroups",   "AWS EC2",        "Low"),
    ("GetSecretValue",           "AWS Secrets",    "Low"),
    ("CreateLogStream",          "AWS CloudWatch", "Low"),
]

def _generate_benign_logs(count: int) -> list[Log]:
    """
    Produce `count` normal background AWS log entries (is_malicious=0).
    These represent legitimate developer activity happening alongside an attack.
    The detection engine will skip them — they should NEVER produce alerts.
    """
    logs = []
    for _ in range(count):
        action, service, severity = random.choice(_BENIGN_ACTIONS)
        logs.append(Log(
            user          = random.choice(USERS),
            action        = action,
            timestamp     = now_str(),          # overwritten by stagger later
            source_ip     = random.choice(INTERNAL_IPS),
            region        = random.choice(SAFE_REGIONS),
            cloud_service = service,
            severity      = severity,
            is_malicious  = 0,
        ))
    return logs


# ── SCENARIO DEFINITIONS ──────────────────────────────────────────────────────

def _scenario_1_cross_domain() -> list[Log]:
    """
    BP1 — Cross-Domain Attack
    Chain: Endpoint → Identity → Cloud Control Plane → Exfiltration
    MITRE: T1566 → T1528 → T1078.004 → T1580 → T1537
    """
    return [
        Log(user="bob@corp.com", action="Endpoint malware execution detected on workstation",
            timestamp="", source_ip=MALICIOUS_IPS[0], region="us-east-1",
            cloud_service="Endpoint Agent", severity="High", is_malicious=1,
            mitre_technique="T1566", mitre_tactic="Initial Access"),

        Log(user="bob@corp.com", action="Identity token extracted from memory via credential dumping",
            timestamp="", source_ip=MALICIOUS_IPS[0], region="us-east-1",
            cloud_service="Azure AD", severity="Critical", is_malicious=1,
            mitre_technique="T1528", mitre_tactic="Credential Access"),

        Log(user="bob@corp.com", action="Cloud console login using stolen token from new IP and region",
            timestamp="", source_ip=MALICIOUS_IPS[1], region="ru-central-1",
            cloud_service="AWS IAM", severity="Critical", is_malicious=1,
            mitre_technique="T1078.004", mitre_tactic="Initial Access"),

        Log(user="bob@corp.com", action="Enumerated all S3 buckets in account",
            timestamp="", source_ip=MALICIOUS_IPS[1], region="ru-central-1",
            cloud_service="AWS S3", severity="High", is_malicious=1,
            mitre_technique="T1580", mitre_tactic="Discovery"),

        Log(user="bob@corp.com", action="Downloaded sensitive files from S3 — transferred 45 GB to external attacker bucket",
            timestamp="", source_ip=MALICIOUS_IPS[1], region="ru-central-1",
            cloud_service="AWS S3", severity="Critical", is_malicious=1,
            mitre_technique="T1537", mitre_tactic="Exfiltration"),
    ]


def _scenario_2_iam_escalation() -> list[Log]:
    """
    BP2 — IAM Privilege Escalation
    Chain: Exposed API → IAM Discovery → Escalation → Evasion → Persistence
    MITRE: T1190 → T1087.004 → T1484.001 → T1562.008 → T1098.001
    """
    return [
        Log(user="svc-deploy", action="Exposed API endpoint exploited — unauthenticated access detected",
            timestamp="", source_ip=MALICIOUS_IPS[2], region="eu-west-1",
            cloud_service="AWS EC2", severity="High", is_malicious=1,
            mitre_technique="T1190", mitre_tactic="Initial Access"),

        Log(user="svc-deploy", action="API call to list all IAM roles and attached policies",
            timestamp="", source_ip=MALICIOUS_IPS[2], region="eu-west-1",
            cloud_service="AWS IAM", severity="Medium", is_malicious=1,
            mitre_technique="T1087.004", mitre_tactic="Discovery"),

        Log(user="svc-deploy", action="Attached AdministratorAccess policy to svc-deploy role",
            timestamp="", source_ip=MALICIOUS_IPS[2], region="eu-west-1",
            cloud_service="AWS IAM", severity="Critical", is_malicious=1,
            mitre_technique="T1484.001", mitre_tactic="Privilege Escalation"),

        Log(user="svc-deploy", action="CloudTrail logging disabled across all regions",
            timestamp="", source_ip=MALICIOUS_IPS[2], region="eu-west-1",
            cloud_service="AWS CloudTrail", severity="Critical", is_malicious=1,
            mitre_technique="T1562.008", mitre_tactic="Defense Evasion"),

        Log(user="svc-deploy", action="New backdoor admin user created: backdoor_svc",
            timestamp="", source_ip=MALICIOUS_IPS[2], region="eu-west-1",
            cloud_service="AWS IAM", severity="Critical", is_malicious=1,
            mitre_technique="T1098.001", mitre_tactic="Persistence"),

        Log(user="backdoor_svc", action="New admin account login confirmed from unknown region",
            timestamp="", source_ip=MALICIOUS_IPS[3], region="cn-north-1",
            cloud_service="AWS IAM", severity="Critical", is_malicious=1,
            mitre_technique="T1078.004", mitre_tactic="Initial Access"),
    ]


def _scenario_3_fileless_malware() -> list[Log]:
    """
    BP3 — Fileless Malware in Container
    Chain: Unverified image → Process exec → In-memory payload → Reverse shell
    MITRE: T1610 → T1059.004 → T1620
    """
    return [
        Log(user="svc-deploy", action="Container image pulled from unverified external registry",
            timestamp="", source_ip=INTERNAL_IPS[0], region="us-east-1",
            cloud_service="Kubernetes", severity="Medium", is_malicious=1,
            mitre_technique="T1610", mitre_tactic="Defense Evasion"),

        Log(user="svc-deploy", action="Suspicious process spawned in container: curl | bash pipe detected",
            timestamp="", source_ip=INTERNAL_IPS[0], region="us-east-1",
            cloud_service="Kubernetes", severity="Critical", is_malicious=1,
            mitre_technique="T1059.004", mitre_tactic="Execution"),

        Log(user="svc-deploy", action="In-memory payload executed — no file written to disk",
            timestamp="", source_ip=INTERNAL_IPS[0], region="us-east-1",
            cloud_service="Kubernetes", severity="Critical", is_malicious=1,
            mitre_technique="T1620", mitre_tactic="Defense Evasion"),

        Log(user="svc-deploy", action="Reverse shell opened from container to external C2 IP",
            timestamp="", source_ip=MALICIOUS_IPS[0], region="us-east-1",
            cloud_service="Kubernetes", severity="Critical", is_malicious=1,
            mitre_technique="T1059.004", mitre_tactic="Execution"),
    ]


def _scenario_4_unusual_login() -> list[Log]:
    """
    BP4 — Unusual Login + Data Exfiltration
    Chain: Valid creds from unusual region → MFA bypass → Discovery → Exfil
    MITRE: T1078.004 → T1078.004 → T1580 → T1530
    """
    return [
        Log(user="alice@corp.com", action="Successful login from unusual region: ap-southeast-1 (first seen for this user)",
            timestamp="", source_ip=MALICIOUS_IPS[3], region="ap-southeast-1",
            cloud_service="AWS IAM", severity="High", is_malicious=1,
            mitre_technique="T1078.004", mitre_tactic="Initial Access"),

        Log(user="alice@corp.com", action="MFA challenge bypassed — social engineering suspected",
            timestamp="", source_ip=MALICIOUS_IPS[3], region="ap-southeast-1",
            cloud_service="AWS IAM", severity="Critical", is_malicious=1,
            mitre_technique="T1078.004", mitre_tactic="Initial Access"),

        Log(user="alice@corp.com", action="Cloud infrastructure discovery — S3 buckets and RDS instances enumerated",
            timestamp="", source_ip=MALICIOUS_IPS[3], region="ap-southeast-1",
            cloud_service="AWS S3", severity="High", is_malicious=1,
            mitre_technique="T1580", mitre_tactic="Discovery"),

        Log(user="alice@corp.com", action="Large data export initiated: 45 GB transferred from S3 to external IP",
            timestamp="", source_ip=MALICIOUS_IPS[3], region="ap-southeast-1",
            cloud_service="AWS S3", severity="Critical", is_malicious=1,
            mitre_technique="T1530", mitre_tactic="Exfiltration"),
    ]


def _scenario_5_multicloud_lateral() -> list[Log]:
    """
    BP5 — Multi-Cloud Lateral Movement
    Chain: CI/CD token theft → AWS → Azure pivot → GCP pivot → Cryptomining
    MITRE: T1552.005 → T1550.001 → T1550.001 → T1496
    """
    return [
        Log(user="admin@corp.com", action="AWS federated token stolen from CI/CD pipeline environment variables",
            timestamp="", source_ip=MALICIOUS_IPS[1], region="us-east-1",
            cloud_service="AWS IAM", severity="Critical", is_malicious=1,
            mitre_technique="T1552.005", mitre_tactic="Credential Access"),

        Log(user="admin@corp.com", action="AWS token used to pivot to Azure via federated trust relationship",
            timestamp="", source_ip=MALICIOUS_IPS[1], region="eu-west-1",
            cloud_service="Azure AD", severity="Critical", is_malicious=1,
            mitre_technique="T1550.001", mitre_tactic="Lateral Movement"),

        Log(user="admin@corp.com", action="Azure identity used to access GCP resources via federated trust — no re-authentication required",
            timestamp="", source_ip=MALICIOUS_IPS[1], region="eu-west-1",
            cloud_service="GCP IAM", severity="Critical", is_malicious=1,
            mitre_technique="T1550.001", mitre_tactic="Lateral Movement"),

        Log(user="admin@corp.com", action="GPU instances deployed across 3 cloud providers for cryptomining",
            timestamp="", source_ip=MALICIOUS_IPS[1], region="cn-north-1",
            cloud_service="AWS EC2", severity="Critical", is_malicious=1,
            mitre_technique="T1496", mitre_tactic="Impact"),
    ]


SCENARIO_MAP = {
    1: _scenario_1_cross_domain,
    2: _scenario_2_iam_escalation,
    3: _scenario_3_fileless_malware,
    4: _scenario_4_unusual_login,
    5: _scenario_5_multicloud_lateral,
}


# ── MAIN ORCHESTRATOR ─────────────────────────────────────────────────────────

def run_simulation(scenario_id: int) -> dict:
    """
    Full simulation pipeline for one scenario.

    Steps:
      1. Generate malicious logs for the scenario
      2. Generate benign background logs
      3. Merge all logs and assign staggered timestamps
      4. Sort chronologically and save to DB
      5. Run detection engine → get alerts
      6. Save alerts to DB (with related_log_id linking back)
      7. Return a result summary dict

    Returns:
        dict with keys: scenario_id, total_logs, malicious_logs,
        benign_logs, alerts_generated, detection_rate_pct, logs, alerts
    """
    if scenario_id not in SCENARIO_MAP:
        return {"error": f"Invalid scenario ID {scenario_id}. Valid: 1–5."}

    logger.info("Starting simulation for scenario %d", scenario_id)

    # ── Step 1 & 2: Generate logs ─────────────────────────────────────
    malicious_logs = SCENARIO_MAP[scenario_id]()
    benign_count   = random.randint(Config.BENIGN_LOG_MIN, Config.BENIGN_LOG_MAX)
    benign_logs    = _generate_benign_logs(benign_count)
    all_logs       = malicious_logs + benign_logs

    # ── Step 3: Stagger timestamps ────────────────────────────────────
    timestamps = staggered_times(
        len(all_logs),
        start_minutes_ago = Config.ATTACK_WINDOW_START,
        spread_minutes    = Config.ATTACK_WINDOW_SPAN,
    )
    random.shuffle(timestamps)   # interleave benign with malicious naturally
    for log, ts in zip(all_logs, timestamps):
        log.timestamp = ts

    # ── Step 4: Sort chronologically and save to DB ───────────────────
    all_logs.sort(key=lambda l: l.timestamp)

    conn    = get_db()
    c       = conn.cursor()
    log_ids = []

    for log in all_logs:
        c.execute(
            """INSERT INTO cloud_logs
               (timestamp, user, action, source_ip, region,
                cloud_service, severity, is_malicious, scenario_id,
                mitre_technique, mitre_tactic)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (log.timestamp, log.user, log.action, log.source_ip, log.region,
             log.cloud_service, log.severity, log.is_malicious, scenario_id,
             log.mitre_technique, log.mitre_tactic),
        )
        log_ids.append(c.lastrowid)

    # ── Step 5: Run detection ─────────────────────────────────────────
    alerts = detect(all_logs, scenario_id)

    # ── Step 6: Save alerts, linking each to the malicious log that triggered it
    malicious_ids = [
        log_ids[i] for i, log in enumerate(all_logs) if log.is_malicious == 1
    ]
    for i, alert in enumerate(alerts):
        alert.related_log_id = malicious_ids[min(i, len(malicious_ids) - 1)]
        alert.timestamp      = now_str()
        c.execute(
            """INSERT INTO alerts
               (type, severity, title, description, timestamp,
                status, related_log_id, best_practice,
                mitre_technique, mitre_tactic)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (alert.type, alert.severity, alert.title, alert.description,
             alert.timestamp, alert.status, alert.related_log_id,
             alert.best_practice, alert.mitre_technique, alert.mitre_tactic),
        )

    conn.commit()
    conn.close()

    # ── Step 7: Build result summary ──────────────────────────────────
    n_malicious     = sum(1 for l in all_logs if l.is_malicious == 1)
    n_benign        = sum(1 for l in all_logs if l.is_malicious == 0)
    detection_rate  = round(safe_divide(len(alerts), n_malicious) * 100, 1)

    logger.info(
        "Scenario %d complete — %d logs (%d malicious, %d benign) → %d alerts (%.0f%% detection rate)",
        scenario_id, len(all_logs), n_malicious, n_benign, len(alerts), detection_rate
    )

    return {
        "scenario_id":        scenario_id,
        "total_logs":         len(all_logs),
        "malicious_logs":     n_malicious,
        "benign_logs":        n_benign,
        "alerts_generated":   len(alerts),
        "detection_rate_pct": detection_rate,
        "logs":               [l.to_dict() for l in all_logs],
        "alerts":             [a.to_dict() for a in alerts],
    }