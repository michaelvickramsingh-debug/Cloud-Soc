"""
routes/alerts.py
----------------
All endpoints that deal with security alerts.

GET /api/alerts              → all alerts, newest first
GET /api/alerts/summary      → count grouped by severity
PUT /api/alerts/<id>/resolve → mark one alert as Resolved
"""

from flask import Blueprint, jsonify
from database.database import get_db
from models.alert      import Alert
from utils.helpers     import api_error
from utils.logger      import get_logger

logger    = get_logger(__name__)
alerts_bp = Blueprint("alerts", __name__)


@alerts_bp.route("/alerts")
def get_alerts():
    """
    Return all alerts, newest first.
    Frontend: Alerts.jsx dashboard
    """
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM alerts ORDER BY timestamp DESC"
    ).fetchall()
    conn.close()
    return jsonify([Alert.from_row(r).to_dict() for r in rows])


@alerts_bp.route("/alerts/summary")
def alerts_summary():
    """
    Return alert count grouped by severity.
    Used for the bar chart on the Home dashboard.

    Response: [{"severity": "Critical", "count": 4}, ...]
    """
    conn = get_db()
    rows = conn.execute(
        "SELECT severity, COUNT(*) as count FROM alerts GROUP BY severity ORDER BY count DESC"
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@alerts_bp.route("/alerts/<int:alert_id>/resolve", methods=["PUT"])
def resolve_alert(alert_id: int):
    """
    Mark one alert as Resolved.
    Frontend: Alerts.jsx resolve button

    Returns 404 if the alert_id doesn't exist.
    """
    conn     = get_db()
    affected = conn.execute(
        "UPDATE alerts SET status='Resolved' WHERE id=?", (alert_id,)
    ).rowcount
    conn.commit()
    conn.close()

    if affected == 0:
        return api_error(f"Alert {alert_id} not found.", 404)

    logger.info("Alert %d resolved.", alert_id)
    return jsonify({"success": True, "id": alert_id, "status": "Resolved"})