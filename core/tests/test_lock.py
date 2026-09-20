from datetime import UTC, datetime, timedelta

from core.lock import DATA_LOCK_UTC, is_before_lock


def test_lock_constant_is_sunday_evening_pacific():
    assert DATA_LOCK_UTC.isoformat() == "2026-09-28T01:00:00+00:00"


def test_one_second_before_is_kept():
    assert is_before_lock(DATA_LOCK_UTC - timedelta(seconds=1))


def test_exactly_at_lock_is_excluded():
    assert not is_before_lock(DATA_LOCK_UTC)


def test_one_second_after_is_excluded():
    assert not is_before_lock(DATA_LOCK_UTC + timedelta(seconds=1))


def test_naive_timestamps_are_utc():
    assert is_before_lock(datetime(2026, 9, 28, 0, 59, 59))
    assert not is_before_lock(datetime(2026, 9, 28, 1, 0, 1, tzinfo=UTC))
