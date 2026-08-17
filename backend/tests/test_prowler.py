"""
tests/test_prowler.py
----------------------
Tests for the Prowler CSPM ingestion service.

Run with:
    cd backend
    pytest tests/test_prowler.py -v

What we test:
  1. Ingestion reads the sample file and creates IOM alerts
  2. Only FAIL findings become alerts — PASS findings are skipped
  3. All ingested alerts have type = 'IOM'
  4. Severity is correctly mapped from Prowler format
  5. MITRE techniques are mapped where known check IDs exist
  6. Summary endpoint returns correct counts
  7. Missing file returns a clear error
  8. Ingesting twice doesn't crash (idempotent-safe)
"""

import sys
import os
import json
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database.database  import init_db, reset_db, get_db
from services.prowler   import ingest_prowler_findings, get_prowler_summary

# Path to our sample Prowler output used in tests
SAMPLE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "prowler_output.json"
)


# ── SETUP ─────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def fresh_db():
    """Start every test with a clean database."""
    init_db()
    reset_db()
    yield
    reset_db()


# ── INGESTION TESTS ───────────────────────────────────────────────────────────

def test_ingest_reads_sample_file():
    """Ingestion should process the sample file without errors."""
    result = ingest_prowler_findings(SAMPLE_FILE)
    assert "error" not in result, f"Ingestion error: {result.get('error')}"


def test_ingest_creates_iom_alerts():
    """All ingested findings should become IOM alerts in the DB."""
    result = ingest_prowler_findings(SAMPLE_FILE)
    assert result["ingested"] > 0, "Should have ingested at least one alert"

    conn   = get_db()
    alerts = conn.execute("SELECT * FROM alerts WHERE type='IOM'").fetchall()
    conn.close()

    assert len(alerts) == result["ingested"]


def test_all_alerts_are_iom_type():
    """Every alert from Prowler must have type='IOM', never 'IOA'."""
    ingest_prowler_findings(SAMPLE_FILE)

    conn   = get_db()
    bad    = conn.execute(
        "SELECT COUNT(*) FROM alerts WHERE type != 'IOM'"
    ).fetchone()[0]
    conn.close()

    assert bad == 0, f"Found {bad} non-IOM alerts after Prowler ingestion"


def test_only_fail_findings_ingested():
    """
    PASS findings should be skipped.
    Our sample file has 5 FAIL findings — all should be ingested,
    and skipped count should be 0 since all are FAIL.
    """
    result = ingest_prowler_findings(SAMPLE_FILE)
    assert result["skipped"] == 0, "Sample file has only FAIL findings — skipped should be 0"
    assert result["ingested"] == 5, "Sample file has exactly 5 FAIL findings"


def test_severity_mapping():
    """Prowler severity strings should map correctly to CloudGuard format."""
    ingest_prowler_findings(SAMPLE_FILE)

    conn     = get_db()
    alerts   = conn.execute("SELECT severity FROM alerts WHERE type='IOM'").fetchall()
    conn.close()

    valid_severities = {"Critical", "High", "Medium", "Low"}
    for a in alerts:
        assert a["severity"] in valid_severities, \
            f"Invalid severity after mapping: {a['severity']}"


def test_mitre_techniques_mapped():
    """
    Alerts with known Prowler check IDs should have MITRE technique IDs.
    Our sample includes guardduty_is_enabled → T1562 and
    iam_root_mfa_enabled → T1078.004
    """
    ingest_prowler_findings(SAMPLE_FILE)

    conn    = get_db()
    mapped  = conn.execute(
        "SELECT COUNT(*) FROM alerts WHERE type='IOM' AND mitre_technique != ''"
    ).fetchone()[0]
    conn.close()

    assert mapped > 0, "At least some Prowler alerts should have MITRE technique IDs"


def test_alerts_have_descriptions():
    """Every ingested alert should have a non-empty description."""
    ingest_prowler_findings(SAMPLE_FILE)

    conn   = get_db()
    alerts = conn.execute(
        "SELECT description FROM alerts WHERE type='IOM'"
    ).fetchall()
    conn.close()

    for a in alerts:
        assert a["description"] and len(a["description"]) > 10, \
            "Alert description is too short or empty"


def test_summary_returns_correct_total():
    """Summary should reflect the number of ingested alerts."""
    result = ingest_prowler_findings(SAMPLE_FILE)
    summary = get_prowler_summary()

    assert summary["total_iom_alerts"] == result["ingested"]


def test_summary_by_severity_breakdown():
    """Summary by_severity should account for all ingested alerts."""
    ingest_prowler_findings(SAMPLE_FILE)
    summary = get_prowler_summary()

    total_from_breakdown = sum(s["count"] for s in summary["by_severity"])
    assert total_from_breakdown == summary["total_iom_alerts"]


def test_missing_file_returns_error():
    """Pointing to a non-existent file should return an error dict."""
    result = ingest_prowler_findings("/nonexistent/path/prowler.json")
    assert "error" in result
    assert "not found" in result["error"].lower()


def test_ingest_twice_does_not_crash():
    """
    Ingesting the same file twice should not crash.
    It will create duplicate alerts (expected behaviour —
    in production you'd reset between runs).
    """
    result1 = ingest_prowler_findings(SAMPLE_FILE)
    result2 = ingest_prowler_findings(SAMPLE_FILE)

    assert "error" not in result1
    assert "error" not in result2


def test_pass_findings_are_skipped():
    """
    A Prowler file with PASS findings should skip them entirely.
    Test with a modified sample that includes PASS findings.
    """
    pass_sample = [
        {
            "message": "MFA is enabled",
            "finding_info": {
                "uid": "prowler-aws-iam_root_mfa_enabled-pass",
                "title": "Root MFA is enabled",
                "desc": "MFA is correctly configured"
            },
            "severity_id": 2,
            "severity": "Low",
            "status": "Passed",
            "status_code": "PASS",
            "status_detail": "MFA is enabled on root account",
            "resources": [{"uid": "arn:aws:iam::123:root", "name": "root",
                           "type": "AwsIamUser", "cloud": {"provider": "aws",
                           "region": "us-east-1", "account": {"uid": "123"}}}],
            "remediation": {"desc": "No action required"},
            "metadata": {"event_code": "iam_root_mfa_enabled"},
            "time": "2026-07-16T10:00:00Z"
        }
    ]

    # Write temp file
    import tempfile
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as f:
        json.dump(pass_sample, f)
        temp_path = f.name

    result = ingest_prowler_findings(temp_path)
    os.unlink(temp_path)

    assert result["ingested"] == 0, "PASS findings should not be ingested"
    assert result["skipped"]  == 1, "PASS finding should be counted as skipped"