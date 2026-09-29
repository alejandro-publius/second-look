"""The study's fixed UTC instants (Update 02 amendment 1, UPDATE_33). Stored times are UTC.

DATA_LOCK_UTC is the first wave's data lock. The first wave's analysis and the server's post_lock
mark read it, and it never moves.

The second wave (plan v3, UPDATE_33) is the sittings whose session started at or after
WAVE2_OPEN_UTC and before SECOND_LOCK_UTC. It does not read the stored post_lock mark: the server
marks every sitting made after the first lock, so every second wave sitting carries it.

Judge mode shows the answers to the photos the study uses. It opened at the first lock, and it is
shut again until JUDGE_MODE_OPENS_UTC, the second lock, so that nobody in the second wave can read
the answers first (docs/deviations.md).
"""

from __future__ import annotations

from datetime import UTC, datetime

DATA_LOCK_UTC = datetime(2026, 9, 28, 1, 0, 0, tzinfo=UTC)
DATA_LOCK_LOCAL_LABEL = "Sunday Sep 27, 2026 at 18:00 PDT"

WAVE2_OPEN_UTC = datetime(2026, 9, 30, 4, 0, 0, tzinfo=UTC)
WAVE2_OPEN_LOCAL_LABEL = "Tuesday Sep 29, 2026 at 21:00 PDT"

SECOND_LOCK_UTC = datetime(2026, 10, 3, 4, 0, 0, tzinfo=UTC)
SECOND_LOCK_LOCAL_LABEL = "Friday Oct 2, 2026 at 21:00 PDT"

JUDGE_MODE_OPENS_UTC = SECOND_LOCK_UTC


def _utc(ts: datetime) -> datetime:
    """Naive timestamps are treated as UTC, as is_before_lock always did."""
    return ts.replace(tzinfo=UTC) if ts.tzinfo is None else ts


def is_before_lock(ts: datetime) -> bool:
    """True if a timestamp is strictly before the lock. Naive timestamps are treated as UTC."""
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return ts < DATA_LOCK_UTC


def is_before_second_lock(ts: datetime) -> bool:
    """True if a timestamp is strictly before the second lock. Naive timestamps are UTC."""
    return _utc(ts) < SECOND_LOCK_UTC


def is_in_wave2(started_at: datetime) -> bool:
    """True if a session that started at this time belongs to the second wave: at or after the
    wave opens and strictly before the second lock. Naive timestamps are UTC."""
    return WAVE2_OPEN_UTC <= _utc(started_at) < SECOND_LOCK_UTC


def is_judge_mode_shut(ts: datetime) -> bool:
    """True while judge mode is shut: strictly before JUDGE_MODE_OPENS_UTC. It does not reopen
    the window in which judge mode was open after the first lock: shut means shut at any time
    before the second lock. Naive timestamps are UTC."""
    return _utc(ts) < JUDGE_MODE_OPENS_UTC
