"""
config.py
---------
Central configuration for CloudGuard backend.
All values are read from .env so you never hardcode secrets.

Usage anywhere in the project:
    from config import Config
    path = Config.DB_PATH
"""

import os
from dotenv import load_dotenv

# Load .env into environment variables
load_dotenv()

class Config:
    # ── Flask ──────────────────────────────────────────────────────
    FLASK_ENV   = os.getenv("FLASK_ENV", "development")
    DEBUG       = os.getenv("FLASK_DEBUG", "True") == "True"
    PORT        = int(os.getenv("PORT", 5000))

    # ── Database ───────────────────────────────────────────────────
    # DB lives at  backend/database/cloudguard.db
    DB_NAME     = os.getenv("DB_NAME", "cloudguard.db")
    DB_PATH     = os.path.join(
        os.path.dirname(__file__),   # backend/
        "database",
        DB_NAME
    )

    # ── Simulation defaults ────────────────────────────────────────
    BENIGN_LOG_MIN  = 3   # min benign logs per simulation run
    BENIGN_LOG_MAX  = 5   # max benign logs per simulation run
    ATTACK_WINDOW_START = 30   # minutes ago the attack begins
    ATTACK_WINDOW_SPAN  = 25   # minutes the attack spreads across