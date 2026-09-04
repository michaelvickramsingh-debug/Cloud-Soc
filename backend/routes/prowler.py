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

import os
import subprocess

from flask import Blueprint, jsonify, request
from services.prowler import ingest_prowler_findings, get_prowler_summary, PROWLER_OUTPUT_PATH
from utils.helpers    import api_error
from utils.logger     import get_logger

logger     = get_logger(__name__)
prowler_bp = Blueprint("prowler", __name__)

# In-memory store of the last scan output (per ECS task)
_last_scan_log = {"stdout": "", "stderr": "", "exit_code": None, "started_at": None, "finished_at": None}


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


@prowler_bp.route("/prowler/scan", methods=["POST"])
def scan():
    """
    Run a Prowler scan against the configured AWS account and ingest results.

    This endpoint shells out to the prowler CLI, writes output to the
    configured data directory, then runs the ingestion pipeline so the
    dashboard populates in one click.

    Optional JSON body:
        {
          "checks": ["iam_root_mfa_enabled", "s3_bucket_public_access"],
          "severity": ["critical", "high"],
          "regions": ["us-east-1"]
        }
    """
    body = request.get_json(silent=True) or {}

    cmd = ["prowler", "aws", "-M", "json-ocsf", "-o", os.path.dirname(PROWLER_OUTPUT_PATH)]

    checks = body.get("checks") or []
    if isinstance(checks, str):
        checks = [checks]
    for check in checks:
        cmd.extend(["-c", check])

    severities = body.get("severity") or []
    if isinstance(severities, str):
        severities = [severities]
    for sev in severities:
        cmd.extend(["--severity", sev])

    regions = body.get("regions") or []
    if isinstance(regions, str):
        regions = [regions]
    for region in regions:
        cmd.extend(["-f", region])

    logger.info("Running Prowler scan: %s", " ".join(cmd))

    import datetime
    _last_scan_log.update({
        "stdout": "",
        "stderr": "",
        "exit_code": None,
        "started_at": datetime.datetime.utcnow().isoformat() + "Z",
        "finished_at": None,
        "command": " ".join(cmd),
    })

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1800,
            check=False,
        )
        _last_scan_log.update({
            "stdout": result.stdout[-8000:],
            "stderr": result.stderr[-4000:],
            "exit_code": result.returncode,
            "finished_at": datetime.datetime.utcnow().isoformat() + "Z",
        })
    except FileNotFoundError:
        _last_scan_log["finished_at"] = datetime.datetime.utcnow().isoformat() + "Z"
        _last_scan_log["stderr"] = "prowler CLI not found"
        logger.error("Prowler CLI not found on backend host")
        return api_error(
            "Prowler CLI is not installed on the backend. "
            "Install it in the backend environment: pip install prowler",
            503,
        )
    except subprocess.TimeoutExpired:
        logger.error("Prowler scan timed out")
        return api_error("Prowler scan timed out after 30 minutes.", 504)
    except Exception as e:
        logger.error("Prowler scan failed to start: %s", str(e))
        return api_error(f"Could not start Prowler scan: {str(e)}", 500)

    if result.returncode != 0:
        logger.error("Prowler scan failed: %s", result.stderr)
        return api_error(
            f"Prowler scan failed (exit {result.returncode}): {result.stderr[:500]}",
            500,
            details={"scan_log": _last_scan_log},
        )

    # Prowler writes prowler_output.ocsf.json; rename/copy to expected path
    generated = os.path.join(os.path.dirname(PROWLER_OUTPUT_PATH), "prowler_output.ocsf.json")
    if os.path.exists(generated):
        try:
            os.replace(generated, PROWLER_OUTPUT_PATH)
        except OSError as e:
            logger.warning("Could not rename Prowler output: %s", e)
            return api_error(f"Could not finalize Prowler output: {str(e)}", 500)

    if not os.path.exists(PROWLER_OUTPUT_PATH):
        return api_error(
            f"Prowler scan completed but output file was not found at {PROWLER_OUTPUT_PATH}",
            500,
        )

    # Auto-ingest the fresh scan so the dashboard updates immediately
    ingest_result = ingest_prowler_findings(PROWLER_OUTPUT_PATH)

    if "error" in ingest_result:
        return api_error(f"Scan succeeded but ingestion failed: {ingest_result['error']}", 500)

    return jsonify({
        "scan_log": _last_scan_log,
        "output_path": PROWLER_OUTPUT_PATH,
        "ingestion": ingest_result,
    })


@prowler_bp.route("/prowler/scan/log")
def scan_log():
    """Return the captured output of the most recent Prowler scan."""
    return jsonify(_last_scan_log)


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