"""UTC timestamp helpers and timezone conversion utilities."""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def utcnow() -> datetime:
    """Return current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def to_user_timezone(dt: datetime, tz_name: str = "Asia/Kolkata") -> datetime:
    """Convert a UTC (or aware) datetime into the user's configured timezone."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(ZoneInfo(tz_name))
