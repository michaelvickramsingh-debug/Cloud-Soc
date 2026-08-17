"""
tests/test_simulation.py
-------------------------
Tests for the simulation and detection pipeline.

Run with:
    cd backend
    pytest tests/ -v

What we test:
  1. All 5 scenarios run without errors
  2. Logs have staggered (unique) timestamps
  3. Every malicious log has a MITRE technique ID
  4. Benign logs never produce alerts
  5. Detection engine produces the right alert types (IOA/IOM)
  6. Detection rate is a sensible number (> 0, <= 100)
  7. The reset function clears logs and alerts
"""

import sys
import os
import pytest

# Make sure Python can find the backend modules
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database.database  import init_db, reset_db, get_db
from services.simulation import run_simulation


# ── SETUP ─────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def fresh_db():
    """Start every test with a clean database."""
    init_db()
    reset_db()
    yield
    reset_db()


# ── SCENARIO TESTS ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("scenario_id", [1, 2, 3, 4, 5])
def test_scenario_runs_without_error(scenario_id):
    """Every scenario should return a result dict with no 'error' key."""
    result = run_simulation(scenario_id)
    assert "error" not in result, f"Scenario {scenario_id} returned error: {result.get('error')}"


@pytest.mark.parametrize("scenario_id", [1, 2, 3, 4, 5])
def test_scenario_generates_logs(scenario_id):
    """Every scenario should generate at least 4 logs (malicious + benign)."""
    result = run_simulation(scenario_id)
    assert result["total_logs"] >= 4


@pytest.mark.parametrize("scenario_id", [1, 2, 3, 4, 5])
def test_scenario_has_malicious_and_benign_logs(scenario_id):
    """Every simulation run must include both malicious and benign logs."""
    result = run_simulation(scenario_id)
    assert result["malicious_logs"] >= 1, "Should have at least 1 malicious log"
    assert result["benign_logs"]    >= 1, "Should have at least 1 benign log"


@pytest.mark.parametrize("scenario_id", [1, 2, 3, 4, 5])
def test_timestamps_are_unique(scenario_id):
    """
    Logs must have staggered timestamps — no two logs share the same second.
    This proves the timeline is realistic for the research paper.
    """
    result     = run_simulation(scenario_id)
    timestamps = [log["timestamp"] for log in result["logs"]]
    assert len(timestamps) == len(set(timestamps)), \
        f"Scenario {scenario_id} has duplicate timestamps: {timestamps}"


@pytest.mark.parametrize("scenario_id", [1, 2, 3, 4, 5])
def test_malicious_logs_have_mitre_ids(scenario_id):
    """Every malicious log must have a non-empty MITRE technique ID."""
    result = run_simulation(scenario_id)
    for log in result["logs"]:
        if log["is_malicious"] == 1:
            assert log["mitre_technique"] != "", \
                f"Malicious log missing MITRE ID: {log['action']}"


# ── DETECTION TESTS ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("scenario_id", [1, 2, 3, 4, 5])
def test_alerts_are_generated(scenario_id):
    """Every scenario should produce at least 1 alert."""
    result = run_simulation(scenario_id)
    assert result["alerts_generated"] >= 1, \
        f"Scenario {scenario_id} produced no alerts"


@pytest.mark.parametrize("scenario_id", [1, 2, 3, 4, 5])
def test_detection_rate_is_sensible(scenario_id):
    """Detection rate should be between 1% and 100%."""
    result = run_simulation(scenario_id)
    rate   = result["detection_rate_pct"]
    assert 0 < rate <= 100, f"Unexpected detection rate for scenario {scenario_id}: {rate}%"


def test_benign_logs_never_trigger_alerts():
    """
    After a simulation run, zero alerts should link to benign log IDs.
    This proves the detection engine correctly ignores benign traffic.
    """
    run_simulation(2)  # scenario 2 has the most rules to test

    conn = get_db()
    # Find any alert whose related_log_id points to a benign log
    bad = conn.execute(
        """SELECT a.id, a.title, l.action, l.is_malicious
           FROM alerts a
           JOIN cloud_logs l ON l.id = a.related_log_id
           WHERE l.is_malicious = 0"""
    ).fetchall()
    conn.close()

    assert len(bad) == 0, \
        f"Found {len(bad)} alert(s) incorrectly linked to benign logs"


def test_alert_types_are_valid():
    """All alerts must have type 'IOA' or 'IOM'."""
    run_simulation(1)
    conn   = get_db()
    alerts = conn.execute("SELECT type FROM alerts").fetchall()
    conn.close()
    for a in alerts:
        assert a["type"] in ("IOA", "IOM"), f"Invalid alert type: {a['type']}"


def test_alert_severities_are_valid():
    """All alerts must use one of the 4 defined severity levels."""
    run_simulation(3)
    conn   = get_db()
    alerts = conn.execute("SELECT severity FROM alerts").fetchall()
    conn.close()
    valid  = {"Critical", "High", "Medium", "Low"}
    for a in alerts:
        assert a["severity"] in valid, f"Invalid severity: {a['severity']}"


# ── RESET TEST ────────────────────────────────────────────────────────────────

def test_reset_clears_logs_and_alerts():
    """
    After reset_db(), logs and alerts tables should be empty.
    Attack scenarios should still be present.
    """
    run_simulation(1)
    run_simulation(2)

    conn = get_db()
    logs_before   = conn.execute("SELECT COUNT(*) FROM cloud_logs").fetchone()[0]
    alerts_before = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
    conn.close()

    assert logs_before   > 0
    assert alerts_before > 0

    reset_db()

    conn = get_db()
    logs_after     = conn.execute("SELECT COUNT(*) FROM cloud_logs").fetchone()[0]
    alerts_after   = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
    scenarios_kept = conn.execute("SELECT COUNT(*) FROM attack_scenarios").fetchone()[0]
    conn.close()

    assert logs_after   == 0, "Logs should be empty after reset"
    assert alerts_after == 0, "Alerts should be empty after reset"
    assert scenarios_kept == 5, "Scenarios should be preserved after reset"


# ── INVALID INPUT TEST ────────────────────────────────────────────────────────

def test_invalid_scenario_id_returns_error():
    """run_simulation with an invalid ID should return an error dict."""
    result = run_simulation(99)
    assert "error" in result