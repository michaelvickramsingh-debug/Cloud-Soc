"""
routes/prowler.py
-----------------
Endpoints for Prowler CSPM findings ingestion.

POST /api/prowler/ingest          → read Prowler JSON file → save IOM alerts
GET  /api/prowler/summary         → IOM alert breakdown by severity/status

How to use:
  1. Run Prowler against your AWS account:
         pip install prowler
         prowler aws -M json-ocsf -o backend/data/
  2. Rename the output file to prowler_output.json
  3. Call POST /api/prowler/ingest
  4. View IOM alerts in GET /api/alerts (type='IOM')
  5. View summary in GET /api/prowler/summary
"""

from flask import Blueprint, jsonify, request
from services.prowler import ingest_prowler_findings, get_prowler_summary
from utils.helpers    import api_error
from utils.logger     import get_logger

logger     = get_logger(__name__)
prowler_bp = Blueprint("prowler", __name__)


@prowler_bp.route("/prowler/ingest", methods=["POST"])
def ingest():
    """
    Ingest Prowler JSON-OCSF findings as IOM alerts.

    Reads from backend/data/prowler_output.json by default.
    You can override the path by passing JSON body:
        {"file_path": "/custom/path/to/prowler.json"}

    Only FAIL findings are ingested — PASS findings are skipped.
    Each FAIL finding becomes one IOM alert in the alerts table.

    Response:
        {
          "total_findings": 150,
          "fail_count": 42,
          "ingested": 42,
          "skipped": 108,
          "by_severity": {"Critical": 3, "High": 15, "Medium": 20, "Low": 4},
          "errors": []
        }
    """
    # Allow optional custom file path in request body
    body      = request.get_json(silent=True) or {}
    file_path = body.get("file_path", None)

    logger.info("Prowler ingest triggered — file_path=%s", file_path or "default")

    result = ingest_prowler_findings(file_path)

    if "error" in result:
        return api_error(result["error"], 400)

    return jsonify(result)


@prowler_bp.route("/prowler/summary")
def summary():
    """
    Return a summary of all Prowler IOM alerts in the database.

    Response:
        {
          "total_iom_alerts": 42,
          "by_severity": [{"severity": "High", "count": 15}, ...],
          "by_status": [{"status": "Open", "count": 40}, ...],
          "recent_findings": [{"title": "...", "severity": "...", ...}]
        }
    """
    return jsonify(get_prowler_summary())