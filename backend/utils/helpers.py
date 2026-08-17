"""
utils/helpers.py
----------------
Small reusable functions used across the project.
None of these belong to a specific service or route.
"""

from datetime import datetime, timedelta
import random


def now_str() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def staggered_times(count: int, start_minutes_ago: int = 30, spread_minutes: int = 25) -> list[str]:
    """
    Generate `count` timestamps spread across a realistic time window.

    Why we need this:
      Real attacks unfold over minutes, not all at the same second.
      If every log shares the same timestamp, the timeline is meaningless.

    Example:
      staggered_times(5, start_minutes_ago=30, spread_minutes=25)
      → 5 timestamps from 30 min ago to 5 min ago, ~5 min apart

    Args:
        count             : how many timestamps to generate
        start_minutes_ago : how far back the first event is
        spread_minutes    : total window the events are spread across

    Returns:
        List of ISO 8601 timestamp strings, in chronological order
    """
    if count <= 0:
        return []

    base = datetime.utcnow() - timedelta(minutes=start_minutes_ago)
    step = spread_minutes / max(count - 1, 1)

    return [
        (base + timedelta(minutes=i * step)).strftime("%Y-%m-%dT%H:%M:%SZ")
        for i in range(count)
    ]


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Divide two numbers safely — returns `default` instead of crashing on zero.

    Usage:
        rate = safe_divide(alerts, malicious_logs) * 100
    """
    if denominator == 0:
        return default
    return numerator / denominator


def api_error(message: str, code: int = 400):
    """
    Standard error response for Flask routes.

    Usage:
        from utils.helpers import api_error
        return api_error("Scenario ID must be 1–5.", 400)
    """
    from flask import jsonify
    return jsonify({"error": message}), code