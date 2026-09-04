"""
routes/stats.py
---------------
Endpoints for dashboard stats, detection metrics, MITRE mapping,
attack simulation, and database reset.

GET  /api/stats         → dashboard summary numbers
GET  /api/metrics       → detection rate, FPR, per-scenario breakdown
GET  /api/mitre         → scenario → MITRE technique mapping
GET  /api/scenarios     → all 5 attack scenario definitions
POST /api/simulate/<id> → run one attack simulation
POST /api/reset         → wipe logs and alerts
"""

from flask import Blueprint, jsonify
from database.database    import get_db, reset_db
from services.simulation  import run_simulation
from utils.helpers        import api_error, safe_divide
from utils.logger         import get_logger

logger   = get_logger(__name__)
stats_bp = Blueprint("stats", __name__)


@stats_bp.route("/stats")
def get_stats():
    """
    Dashboard summary counts.
    Frontend: Home.jsx stats grid
    """
    conn = get_db()
    c    = conn.cursor()

    simulated_logs = c.execute("SELECT COUNT(*) FROM cloud_logs").fetchone()[0]
    live_logs = c.execute("SELECT COUNT(*) FROM logs").fetchone()[0]

    data = {
        "total_logs":     simulated_logs + live_logs,
        "live_logs":      live_logs,
        "total_alerts":   c.execute("SELECT COUNT(*) FROM alerts").fetchone()[0],
        "critical":       c.execute("SELECT COUNT(*) FROM alerts WHERE severity='Critical'").fetchone()[0],
        "high":           c.execute("SELECT COUNT(*) FROM alerts WHERE severity='High'").fetchone()[0],
        "medium":         c.execute("SELECT COUNT(*) FROM alerts WHERE severity='Medium'").fetchone()[0],
        "open_alerts":    c.execute("SELECT COUNT(*) FROM alerts WHERE status='Open'").fetchone()[0],
        "malicious_logs": c.execute("SELECT COUNT(*) FROM cloud_logs WHERE is_malicious=1").fetchone()[0],
        "benign_logs":    c.execute("SELECT COUNT(*) FROM cloud_logs WHERE is_malicious=0").fetchone()[0],
    }
    conn.close()
    return jsonify(data)


@stats_bp.route("/metrics")
def get_metrics():
    """
    Detection performance metrics across all simulation runs.
    Used in the research paper findings section.

    Key metrics:
      detection_rate_pct   : alerts generated / malicious logs × 100
      false_positive_rate  : always 0 — benign logs never trigger alerts by design
      by_scenario          : per-scenario breakdown for the paper's results table
    """
    conn = get_db()
    c    = conn.cursor()

    total_malicious = c.execute("SELECT COUNT(*) FROM cloud_logs WHERE is_malicious=1").fetchone()[0]
    total_benign    = c.execute("SELECT COUNT(*) FROM cloud_logs WHERE is_malicious=0").fetchone()[0]
    total_alerts    = c.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
    open_alerts     = c.execute("SELECT COUNT(*) FROM alerts WHERE status='Open'").fetchone()[0]
    resolved_alerts = c.execute("SELECT COUNT(*) FROM alerts WHERE status='Resolved'").fetchone()[0]

    # Per-scenario breakdown.
    # cloud_logs and alerts are aggregated in separate subqueries before
    # joining to attack_scenarios — joining both child tables directly would
    # fan-out (a scenario with N logs and M alerts produces N*M matched rows),
    # silently inflating SUM(l.is_malicious) and even driving benign_logs
    # negative once a scenario has more than one alert.
    rows = c.execute(
        """SELECT
               s.id,
               s.name,
               COALESCE(log_stats.total_logs, 0)     AS total_logs,
               COALESCE(log_stats.malicious_logs, 0)  AS malicious_logs,
               COALESCE(log_stats.total_logs, 0) - COALESCE(log_stats.malicious_logs, 0) AS benign_logs,
               COALESCE(alert_stats.alert_count, 0)   AS alert_count
           FROM attack_scenarios s
           LEFT JOIN (
               SELECT scenario_id,
                      COUNT(*)         AS total_logs,
                      SUM(is_malicious) AS malicious_logs
               FROM cloud_logs
               GROUP BY scenario_id
           ) log_stats ON log_stats.scenario_id = s.id
           LEFT JOIN (
               SELECT best_practice, COUNT(*) AS alert_count
               FROM alerts
               GROUP BY best_practice
           ) alert_stats ON alert_stats.best_practice = s.id
           ORDER BY s.id"""
    ).fetchall()
    conn.close()

    by_scenario = []
    for row in rows:
        r   = dict(row)
        mal = r["malicious_logs"] or 0
        alt = r["alert_count"]    or 0
        r["detection_rate_pct"] = round(safe_divide(alt, mal) * 100, 1)
        by_scenario.append(r)

    return jsonify({
        "total_malicious_logs": total_malicious,
        "total_benign_logs":    total_benign,
        "total_alerts":         total_alerts,
        "open_alerts":          open_alerts,
        "resolved_alerts":      resolved_alerts,
        "detection_rate_pct":   round(safe_divide(total_alerts, total_malicious) * 100, 1),
        "false_positive_rate":  0,
        "by_scenario":          by_scenario,
    })


@stats_bp.route("/mitre")
def get_mitre():
    """
    All MITRE ATT&CK technique IDs seen across simulation runs,
    grouped by scenario and tactic.
    Used for the research paper's MITRE mapping table.
    """
    conn = get_db()
    rows = conn.execute(
        """SELECT
               l.scenario_id,
               s.name            AS scenario_name,
               l.mitre_tactic,
               l.mitre_technique,
               COUNT(*)          AS occurrences
           FROM cloud_logs l
           JOIN attack_scenarios s ON s.id = l.scenario_id
           WHERE l.is_malicious    = 1
             AND l.mitre_technique != ''
           GROUP BY l.scenario_id, s.name, l.mitre_tactic, l.mitre_technique
           ORDER BY l.scenario_id, l.mitre_tactic, l.mitre_technique"""
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@stats_bp.route("/scenarios")
def get_scenarios():
    """All 5 attack scenario definitions. Frontend: Home.jsx, BestPractice.jsx"""
    conn = get_db()
    rows = conn.execute("SELECT * FROM attack_scenarios ORDER BY id").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@stats_bp.route("/practices")
def get_practices():
    """Return the Best Practice guide content used by the frontend.

    The UI expects this endpoint to exist so the simulation page can stay
    in live mode even when the backend is deployed separately from the
    frontend build.
    """
    return jsonify([
        {
            "id": 1,
            "title": "Threat Intelligence",
            "summary": "Correlate cloud activity against known adversary tradecraft instead of reacting to isolated alerts.",
            "key_insight": "Attackers reuse the same cloud-specific techniques across campaigns — recognizing the pattern early cuts detection time dramatically.",
            "what_without": "Analysts see a stream of disconnected, low-context alerts and can't tell a real intrusion from noise until damage is already done.",
            "what_with": "Alerts are enriched with adversary context, so the SOC recognizes a known attack pattern in progress and responds before it escalates.",
        },
        {
            "id": 2,
            "title": "Control Plane Context",
            "summary": "Understand identity, permissions, and configuration changes — the cloud control plane is the new perimeter.",
            "key_insight": "Most cloud breaches involve control-plane misuse (IAM, roles, policies) rather than traditional malware on a host.",
            "what_without": "A privilege escalation via a misconfigured IAM policy looks like routine admin activity and goes unnoticed for days or weeks.",
            "what_with": "Every permission and policy change is tracked with context, so an unauthorized privilege escalation is flagged the moment it happens.",
        },
        {
            "id": 3,
            "title": "Runtime Protection",
            "summary": "Monitor workloads (containers, serverless, VMs) as they execute, not just their static configuration.",
            "key_insight": "Fileless and in-memory techniques evade traditional scanning because there's no file ever written to disk.",
            "what_without": "A reverse shell spawned inside a container runs silently — nothing on disk ever gets scanned, so nothing gets caught.",
            "what_with": "Runtime behavior is monitored directly, so anomalous process activity inside a container or function is caught as it happens.",
        },
        {
            "id": 4,
            "title": "Cloud Expertise",
            "summary": "Cloud-native attacks require analysts fluent in cloud services, not just traditional network/endpoint security.",
            "key_insight": "A login from an unusual region or an unfamiliar API call pattern only looks suspicious to someone who knows what 'normal' looks like for that cloud environment.",
            "what_without": "An analyst without cloud-specific training dismisses an impossible-travel login alert as a false positive.",
            "what_with": "Cloud-fluent analysts recognize subtle deviations from normal cloud usage and investigate them before they become a breach.",
        },
        {
            "id": 5,
            "title": "Automate Response",
            "summary": "Machine-speed attacks need machine-speed containment — manual response can't keep pace in the cloud.",
            "key_insight": "Cloud resources (compute, storage, credentials) can be created, escalated, and abused within minutes, far faster than a human-driven response process.",
            "what_without": "By the time an analyst manually revokes a compromised credential, the attacker has already pivoted to other resources.",
            "what_with": "Automated playbooks isolate compromised resources and revoke credentials within seconds of detection, containing the blast radius.",
        },
    ])


@stats_bp.route("/simulate/<int:scenario_id>", methods=["POST"])
def simulate(scenario_id: int):
    """
    Run one attack simulation.
    Generates malicious + benign logs, runs detection, saves everything to DB.
    Frontend: BestPractice.jsx run button
    """
    if scenario_id not in range(1, 6):
        return api_error("Scenario ID must be between 1 and 5.", 400)

    result = run_simulation(scenario_id)

    if "error" in result:
        return api_error(result["error"], 400)

    return jsonify(result)


@stats_bp.route("/reset", methods=["POST"])
def reset():
    """
    Wipe all logs and alerts. Attack scenario seeds are kept.
    Use this between demo runs so the dashboard starts clean.
    """
    reset_db()
    return jsonify({"success": True, "message": "All logs and alerts cleared. Scenarios preserved."})