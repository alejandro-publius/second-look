"""The one UTC data lock constant (Update 02 amendment 1). Stored times are UTC."""

from __future__ import annotations

from datetime import UTC, datetime

DATA_LOCK_UTC = datetime(2026, 9, 28, 1, 0, 0, tzinfo=UTC)
DATA_LOCK_LOCAL_LABEL = "Sunday Sep 27, 2026 at 18:00 PDT"


def is_before_lock(ts: datetime) -> bool:
    """True if a timestamp is strictly before the lock. Naive timestamps are treated as UTC."""
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return ts < DATA_LOCK_UTC
