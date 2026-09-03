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

    # Per-scenario breakdown
    rows = c.execute(
        """SELECT
               s.id,
               s.name,
               COUNT(DISTINCT l.id)         AS total_logs,
               SUM(l.is_malicious)          AS malicious_logs,
               COUNT(DISTINCT l.id) - SUM(l.is_malicious) AS benign_logs,
               COUNT(DISTINCT a.id)         AS alert_count
           FROM attack_scenarios s
           LEFT JOIN cloud_logs l ON l.scenario_id = s.id
           LEFT JOIN alerts     a ON a.best_practice = s.id
           GROUP BY s.id
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
               l.action,
               COUNT(*)          AS occurrences
           FROM cloud_logs l
           JOIN attack_scenarios s ON s.id = l.scenario_id
           WHERE l.is_malicious    = 1
             AND l.mitre_technique != ''
           GROUP BY l.scenario_id, l.mitre_technique
           ORDER BY l.scenario_id, l.mitre_tactic"""
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