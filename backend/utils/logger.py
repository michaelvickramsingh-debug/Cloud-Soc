"""
utils/logger.py
---------------
Centralised logging for the entire backend.

Why not just use print()?
  - Logs include timestamps and which file the message came from
  - You can turn DEBUG messages off in production by changing LOG_LEVEL
  - All logs go to the same format so they're easy to read

Usage in any file:
    from utils.logger import get_logger
    logger = get_logger(__name__)

    logger.info("Simulation started for scenario %d", scenario_id)
    logger.warning("No logs found for scenario %d", scenario_id)
    logger.error("Database error: %s", str(e))
"""

import logging
import os


LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG")

def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger with a clean format.
    Call this at the top of every module that needs logging.
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            "[%(asctime)s] %(levelname)s %(name)s — %(message)s",
            datefmt="%H:%M:%S"
        ))
        logger.addHandler(handler)

    logger.setLevel(getattr(logging, LOG_LEVEL, logging.DEBUG))
    return logger