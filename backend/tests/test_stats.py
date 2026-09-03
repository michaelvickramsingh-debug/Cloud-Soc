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
