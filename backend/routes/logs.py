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
    Return up to 200 log entries from both cloud_logs (simulations) and logs (live), newest first.
    Frontend: Logs.jsx viewer
    """
    conn = get_db()

    # Get cloud_logs (simulated)
    cloud_rows = conn.execute(
        'SELECT id, timestamp, "user", action as event, source_ip as ip, region, cloud_service as source, severity FROM cloud_logs ORDER BY timestamp DESC LIMIT 100'
    ).fetchall()

    # Get live logs
    live_rows = conn.execute(
        'SELECT id, timestamp, "user", event, ip, region, source, status FROM logs ORDER BY timestamp DESC LIMIT 100'
    ).fetchall()

    conn.close()

    # Convert both to dicts
    logs_list = []

    # Add cloud_logs (simulated)
    for r in cloud_rows:
        logs_list.append({
            'id': r[0],
            'timestamp': r[1],
            'user': r[2],
            'event': r[3],
            'ip': r[4],
            'region': r[5],
            'source': r[6],
            'severity': r[7] or 'Low',
            'type': 'simulated'
        })

    # Add live logs
    for r in live_rows:
        logs_list.append({
            'id': r[0],
            'timestamp': r[1],
            'user': r[2],
            'event': r[3],
            'ip': r[4],
            'region': r[5],
            'source': r[6],
            'status': r[7],
            'severity': 'Medium',
            'type': 'live'
        })

    # Sort by timestamp descending and return top 200
    logs_list.sort(key=lambda x: x['timestamp'], reverse=True)
    return jsonify(logs_list[:200])


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