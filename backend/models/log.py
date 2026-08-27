"""
models/log.py
-------------
Defines what ONE cloud log entry looks like as a Python object.

Why models?
  Instead of passing raw dicts around everywhere, we use a dataclass.
  This means:
    - Every part of the code knows exactly what fields a Log has
    - You get autocompletion in VS Code
    - Bugs from typos like log["timestmap"] are caught early

Usage:
    from models.log import Log
    log = Log(user="alice@corp.com", action="ListBuckets", ...)
    log.to_dict()   # → plain dict for JSON response
"""

from dataclasses import dataclass, field, asdict


@dataclass
class Log:
    # Required fields (must be provided when creating a Log)
    user:            str
    action:          str
    timestamp:       str

    # Optional fields with sensible defaults
    source_ip:       str  = ""
    region:          str  = ""
    cloud_service:   str  = ""
    severity:        str  = "Low"
    is_malicious:    int  = 0          # 0 = benign, 1 = malicious
    scenario_id:     int  = 0
    mitre_technique: str  = ""
    mitre_tactic:    str  = ""

    # Auto-assigned by the DB after INSERT — not set by us
    id:              int  = 0

    def to_dict(self) -> dict:
        """Convert to plain dict for JSON serialisation."""
        return asdict(self)

    @staticmethod
    def from_row(row) -> "Log":
        """
        Build a Log from a sqlite3.Row object.
        Used when reading logs back out of the database.

        Example:
            rows = conn.execute("SELECT * FROM cloud_logs").fetchall()
            logs = [Log.from_row(r) for r in rows]
        """
        return Log(
            id              = row["id"],
            timestamp       = row["timestamp"],
            user            = row["user"],
            action          = row["action"],
            source_ip       = row["source_ip"]       or "",
            region          = row["region"]           or "",
            cloud_service   = row["cloud_service"]    or "",
            severity        = row["severity"]         or "Low",
            is_malicious    = row["is_malicious"]     or 0,
            scenario_id     = row["scenario_id"]      or 0,
            mitre_technique = row["mitre_technique"]  or "",
            mitre_tactic    = row["mitre_tactic"]     or "",
        )