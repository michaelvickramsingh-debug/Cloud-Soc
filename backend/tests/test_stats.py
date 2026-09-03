"""
Tests for dashboard statistics across simulated and live CloudTrail logs.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import app
from database.database import get_db, init_db, reset_db


class TestStats(unittest.TestCase):
    def setUp(self):
        init_db()
        reset_db()

    def tearDown(self):
        reset_db()

    def test_stats_include_live_cloudtrail_logs(self):
        conn = get_db()
        conn.execute(
            """INSERT INTO cloud_logs (
                   timestamp, "user", action, is_malicious
               ) VALUES (?, ?, ?, ?)""",
            ("2026-09-02T06:00:00Z", "simulated-user", "SimulatedAction", 1),
        )
        conn.execute(
            """INSERT INTO logs (
                   timestamp, "user", event
               ) VALUES (?, ?, ?)""",
            ("2026-09-02T06:01:00Z", "cloudtrail-user", "DescribeRegions"),
        )
        conn.commit()
        conn.close()

        response = app.test_client().get("/api/stats")

        self.assertEqual(response.status_code, 200)
        stats = response.get_json()
        self.assertEqual(stats["total_logs"], 2)
        self.assertEqual(stats["live_logs"], 1)
        self.assertEqual(stats["malicious_logs"], 1)
        self.assertEqual(stats["benign_logs"], 0)

    def test_metrics_by_scenario_not_inflated_by_multiple_alerts(self):
        """
        Regression test: /api/metrics used to join cloud_logs and alerts
        directly to attack_scenarios in one query. When a scenario had more
        than one alert, that join fanned out (N logs x M alerts rows),
        inflating SUM(is_malicious) and even driving benign_logs negative.
        """
        conn = get_db()
        cursor = conn.cursor()

        # 2 malicious + 1 benign log for scenario 1
        cursor.executemany(
            """INSERT INTO cloud_logs (
                   timestamp, "user", action, is_malicious, scenario_id
               ) VALUES (?, ?, ?, ?, ?)""",
            [
                ("2026-09-03T06:00:00Z", "attacker", "PutUserPolicy", 1, 1),
                ("2026-09-03T06:00:01Z", "attacker", "DeleteBucket", 1, 1),
                ("2026-09-03T06:00:02Z", "alice", "GetObject", 0, 1),
            ],
        )
        # 2 alerts linked to scenario 1 via best_practice — this is what
        # previously triggered the fan-out.
        cursor.executemany(
            """INSERT INTO alerts (
                   type, severity, title, description, timestamp, best_practice
               ) VALUES (?, ?, ?, ?, ?, ?)""",
            [
                ("IOA", "Critical", "Alert A", "desc", "2026-09-03T06:00:00Z", 1),
                ("IOA", "High", "Alert B", "desc", "2026-09-03T06:00:01Z", 1),
            ],
        )
        conn.commit()
        conn.close()

        response = app.test_client().get("/api/metrics")

        self.assertEqual(response.status_code, 200)
        by_scenario = {row["id"]: row for row in response.get_json()["by_scenario"]}
        scenario_1 = by_scenario[1]

        self.assertEqual(scenario_1["total_logs"], 3)
        self.assertEqual(scenario_1["malicious_logs"], 2)
        self.assertEqual(scenario_1["benign_logs"], 1)
        self.assertEqual(scenario_1["alert_count"], 2)

    def test_reset_clears_live_cloudtrail_logs(self):
        conn = get_db()
        conn.execute(
            """INSERT INTO logs (
                   timestamp, "user", event
               ) VALUES (?, ?, ?)""",
            ("2026-09-02T06:00:00Z", "cloudtrail-user", "DescribeRegions"),
        )
        conn.commit()
        conn.close()

        reset_db()

        conn = get_db()
        live_log_count = conn.execute("SELECT COUNT(*) FROM logs").fetchone()[0]
        conn.close()
        self.assertEqual(live_log_count, 0)
