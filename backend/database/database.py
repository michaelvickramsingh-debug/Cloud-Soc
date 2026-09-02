import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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


class PostgreSQLCursor:
    """Translate the application's SQLite-style placeholders for PostgreSQL."""

    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, statement, parameters=None):
        if parameters is None:
            self._cursor.execute(statement.replace("?", "%s"))
        else:
            self._cursor.execute(statement.replace("?", "%s"), parameters)
        return self

    def executemany(self, statement, parameters):
        self._cursor.executemany(statement.replace("?", "%s"), parameters)
        return self

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class PostgreSQLConnection:
    """Expose the SQLite connection methods used by the application."""

    def __init__(self, database_url):
        import psycopg2
        from psycopg2.extras import DictCursor

        self._connection = psycopg2.connect(database_url, cursor_factory=DictCursor)

    def cursor(self):
        return PostgreSQLCursor(self._connection.cursor())

    def execute(self, statement, parameters=None):
        cursor = self.cursor()
        return cursor.execute(statement, parameters)

    def commit(self):
        self._connection.commit()

    def close(self):
        self._connection.close()


def get_db():
    """
    Open and return a SQLite connection.
    conn.row_factory = sqlite3.Row lets you access columns by name:
        row["timestamp"]  instead of  row[0]
    """
    if Config.DB_TYPE == "postgresql":
        if not Config.DATABASE_URL:
            raise RuntimeError("DATABASE_URL must be set when DB_TYPE is postgresql")
        return PostgreSQLConnection(Config.DATABASE_URL)

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
    schema_name = (
        "schema.postgresql.sql" if Config.DB_TYPE == "postgresql" else "schema.sql"
    )
    schema_path = os.path.join(os.path.dirname(__file__), schema_name)
    with open(schema_path, "r") as f:
        schema_sql = f.read()

    conn = get_db()
    if Config.DB_TYPE == "postgresql":
        conn.cursor().execute(schema_sql)
    else:
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
    conn.cursor().executemany(
        """INSERT INTO attack_scenarios VALUES (?,?,?,?,?,?,?)
           ON CONFLICT (id) DO NOTHING""",
        scenarios,
    )