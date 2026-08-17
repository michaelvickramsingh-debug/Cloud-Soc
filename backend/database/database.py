"""
database/database.py
--------------------
Handles everything SQLite:
  - get_db()   : open a connection with Row factory
  - init_db()  : create tables from schema.sql + seed scenarios
  - reset_db() : wipe logs & alerts (scenarios stay)

Why separate from models?
  Models (log.py, alert.py) define the shape of one record.
  This file handles the database itself — connections and setup.
"""

import os
import sqlite3
from config import Config
from utils.logger import get_logger

logger = get_logger(__name__)


def get_db() -> sqlite3.Connection:
    """
    Open and return a SQLite connection.
    conn.row_factory = sqlite3.Row lets you access columns by name:
        row["timestamp"]  instead of  row[0]
    """
    conn = sqlite3.connect(Config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")   # enforce FK constraints
    return conn


def init_db():
    """
    Create tables (reads schema.sql) and seed attack scenarios.
    Safe to call on every startup — all statements use IF NOT EXISTS.
    """
    # Ensure the database/ directory exists
    os.makedirs(os.path.dirname(Config.DB_PATH), exist_ok=True)

    # Load and execute the SQL schema file
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path, "r") as f:
        schema_sql = f.read()

    conn = get_db()
    conn.executescript(schema_sql)

    # Seed attack scenarios (INSERT OR IGNORE = safe on restart)
    _seed_scenarios(conn)

    conn.commit()
    conn.close()
    logger.info("Database initialised at %s", Config.DB_PATH)


def reset_db():
    """
    Delete all logs and alerts.
    Attack scenario seeds are KEPT so the frontend still works.
    Call this between demo runs via POST /api/reset.
    """
    conn = get_db()
    conn.execute("DELETE FROM alerts")
    conn.execute("DELETE FROM cloud_logs")
    conn.commit()
    conn.close()
    logger.info("Database reset — logs and alerts cleared.")


# ── PRIVATE ───────────────────────────────────────────────────────────────────

def _seed_scenarios(conn: sqlite3.Connection):
    scenarios = [
        (
            1,
            "Cross-Domain Attack",
            "Attacker compromises endpoint, steals identity token, pivots to cloud.",
            "Credential Theft + Token Abuse",
            "Identity → Cloud Control Plane",
            "Best Practice 1: Adopt an Adversary-Led Approach",
            "Initial Access, Credential Access, Lateral Movement, Exfiltration",
        ),
        (
            2,
            "IAM Privilege Escalation",
            "Attacker exploits exposed API, escalates IAM role to admin.",
            "API Abuse + IAM Manipulation",
            "Control Plane",
            "Best Practice 2: Implement Real-Time Cloud-Native Detections",
            "Initial Access, Privilege Escalation, Defense Evasion, Persistence",
        ),
        (
            3,
            "Fileless Malware in Container",
            "Malware executes in container memory — no file written to disk.",
            "In-Memory Execution",
            "Workload / Container",
            "Best Practice 3: Accelerate Investigations with Unified Cloud Context",
            "Execution, Defense Evasion",
        ),
        (
            4,
            "Unusual Login + Data Exfiltration",
            "Attacker uses valid credentials from unusual region, exfiltrates S3 data.",
            "Valid Account Abuse",
            "Identity + Data Layer",
            "Best Practice 4: Automate and Scale Response",
            "Initial Access, Discovery, Exfiltration",
        ),
        (
            5,
            "Multi-Cloud Lateral Movement",
            "Attacker steals CI/CD token, pivots from AWS → Azure → GCP.",
            "Token Theft + Lateral Movement",
            "Multi-Cloud Identity",
            "Best Practice 5: Partner with Cloud Experts",
            "Credential Access, Lateral Movement, Impact",
        ),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO attack_scenarios VALUES (?,?,?,?,?,?,?)",
        scenarios,
    )