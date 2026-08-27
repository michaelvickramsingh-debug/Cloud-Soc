import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    FLASK_ENV  = os.getenv("FLASK_ENV", "development")
    DEBUG      = os.getenv("FLASK_DEBUG", "True") == "True"
    PORT       = int(os.getenv("PORT", 5001))
    DB_NAME    = os.getenv("DB_NAME", "cloudguard.db")
    DB_PATH    = os.path.join(os.path.dirname(__file__), "database", DB_NAME)
    BENIGN_LOG_MIN       = 3
    BENIGN_LOG_MAX       = 5
    ATTACK_WINDOW_START  = 30
    ATTACK_WINDOW_SPAN   = 25
