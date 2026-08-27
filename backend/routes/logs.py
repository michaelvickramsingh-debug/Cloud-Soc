"""
routes/logs.py
--------------
All endpoints that deal with cloud logs.

GET /api/logs              → all logs, newest first
GET /api/logs/timeline/<id> → one scenario in chronological order with time deltas
"""

from datetime import datetime
from flask import Blueprint, jsonify
from database.database import get_db
from models.log        import Log
from utils.helpers     import api_error
from utils.logger      import get_logger

logger   = get_logger(__name__)
logs_bp  = Blueprint("logs", __name__)


@logs_bp.route("/logs")
def get_logs():
    """
    Return up to 200 log entries, newest first.
    Frontend: Logs.jsx viewer
    """
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM cloud_logs ORDER BY timestamp DESC LIMIT 200"
    ).fetchall()
    conn.close()
    return jsonify([Log.from_row(r).to_dict() for r in rows])


@logs_bp.route("/logs/timeline/<int:scenario_id>")
def get_timeline(scenario_id: int):
    """
    Return all logs for one scenario in chronological order.
    Each event includes:
      - step          : sequence number (1, 2, 3 …)
      - delta_seconds : seconds elapsed since the first event

    Why this matters for research:
      This endpoint proves the attack unfolded over a realistic time window
      and lets the paper show the chronological tactic chain.

    Frontend: Timeline.jsx (Phase B)
    """
    if scenario_id not in range(1, 6):
        return api_error("Scenario ID must be between 1 and 5.", 400)

    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM cloud_logs WHERE scenario_id=? ORDER BY timestamp ASC",
        (scenario_id,)
    ).fetchall()
    conn.close()

    if not rows:
        return jsonify({
            "scenario_id": scenario_id,
            "events":      [],
            "message":     "No logs yet. Run POST /api/simulate/<id> first.",
        })

    events     = []
    first_time = None

    for i, row in enumerate(rows):
        log = Log.from_row(row)
        try:
            t = datetime.strptime(log.timestamp, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            t = datetime.utcnow()

        if first_time is None:
            first_time = t

        delta = int((t - first_time).total_seconds())

        event = log.to_dict()
        event["step"]          = i + 1
        event["delta_seconds"] = delta
        events.append(event)

    return jsonify({"scenario_id": scenario_id, "total_events": len(events), "events": events})