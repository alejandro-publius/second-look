from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from core import lock
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


# The second wave and judge mode (UPDATE_33) ------------------------------------------------------


def test_the_first_lock_did_not_move():
    # The first wave's analysis and the server's post_lock mark read these two.
    assert DATA_LOCK_UTC == datetime(2026, 9, 28, 1, 0, 0, tzinfo=UTC)
    assert lock.DATA_LOCK_LOCAL_LABEL == "Sunday Sep 27, 2026 at 18:00 PDT"


def test_the_second_lock_is_48_hours_before_the_deadline():
    deadline = datetime(2026, 10, 5, 4, 0, 0, tzinfo=UTC)  # Sun Oct 4, 21:00 PDT
    assert lock.SECOND_LOCK_UTC.isoformat() == "2026-10-03T04:00:00+00:00"
    assert deadline - lock.SECOND_LOCK_UTC == timedelta(hours=48)


def test_the_wave_opens_after_the_first_lock_and_before_the_second():
    assert lock.WAVE2_OPEN_UTC.isoformat() == "2026-09-30T04:00:00+00:00"
    assert DATA_LOCK_UTC < lock.WAVE2_OPEN_UTC < lock.SECOND_LOCK_UTC


def test_each_local_label_is_its_instant_in_pacific_time():
    pacific = ZoneInfo("America/Los_Angeles")
    pairs = [
        (DATA_LOCK_UTC, lock.DATA_LOCK_LOCAL_LABEL),
        (lock.WAVE2_OPEN_UTC, lock.WAVE2_OPEN_LOCAL_LABEL),
        (lock.SECOND_LOCK_UTC, lock.SECOND_LOCK_LOCAL_LABEL),
    ]
    for instant, label in pairs:
        local = instant.astimezone(pacific)
        written = f"{local:%A %b} {local.day}, {local.year} at {local:%H:%M} {local.tzname()}"
        assert label == written


def test_judge_mode_opens_at_the_second_lock():
    assert lock.JUDGE_MODE_OPENS_UTC == lock.SECOND_LOCK_UTC


def test_judge_mode_is_shut_until_the_second_lock_and_open_from_it_on():
    opens = lock.JUDGE_MODE_OPENS_UTC
    assert lock.is_judge_mode_shut(opens - timedelta(seconds=1))
    assert not lock.is_judge_mode_shut(opens)
    assert not lock.is_judge_mode_shut(opens + timedelta(seconds=1))


def test_judge_mode_is_shut_at_every_moment_it_was_open_after_the_first_lock():
    # It was open from the first lock until the deploy of UPDATE_33. The rule has no such window.
    for moment in (
        DATA_LOCK_UTC - timedelta(days=3),
        DATA_LOCK_UTC,
        DATA_LOCK_UTC + timedelta(seconds=1),
        datetime(2026, 9, 29, 12, 0, 0, tzinfo=UTC),
        lock.WAVE2_OPEN_UTC,
    ):
        assert lock.is_judge_mode_shut(moment), moment


def test_judge_mode_reads_naive_timestamps_as_utc():
    assert lock.is_judge_mode_shut(datetime(2026, 10, 3, 3, 59, 59))
    assert not lock.is_judge_mode_shut(datetime(2026, 10, 3, 4, 0, 0))
    # 21:00 in Pacific time on Oct 2 is the second lock itself.
    pacific = ZoneInfo("America/Los_Angeles")
    assert not lock.is_judge_mode_shut(datetime(2026, 10, 2, 21, 0, 0, tzinfo=pacific))
    assert lock.is_judge_mode_shut(datetime(2026, 10, 2, 20, 59, 59, tzinfo=pacific))


def test_before_the_second_lock_is_strict():
    assert lock.is_before_second_lock(lock.SECOND_LOCK_UTC - timedelta(seconds=1))
    assert not lock.is_before_second_lock(lock.SECOND_LOCK_UTC)
    assert lock.is_before_second_lock(datetime(2026, 10, 3, 3, 59, 59))


def test_wave_2_is_from_its_opening_up_to_the_second_lock():
    assert not lock.is_in_wave2(lock.WAVE2_OPEN_UTC - timedelta(seconds=1))
    assert lock.is_in_wave2(lock.WAVE2_OPEN_UTC)
    assert lock.is_in_wave2(lock.SECOND_LOCK_UTC - timedelta(seconds=1))
    assert not lock.is_in_wave2(lock.SECOND_LOCK_UTC)
    assert not lock.is_in_wave2(lock.SECOND_LOCK_UTC + timedelta(seconds=1))
    assert lock.is_in_wave2(datetime(2026, 9, 30, 4, 0, 0))


def test_no_first_wave_sitting_is_in_wave_2_and_every_wave_2_sitting_is_after_the_first_lock():
    # The first wave is the sittings before the first lock. The server marks every later one
    # post_lock, so wave 2 cannot go by that mark: it goes by the start time.
    assert not lock.is_in_wave2(DATA_LOCK_UTC - timedelta(seconds=1))
    assert not lock.is_in_wave2(DATA_LOCK_UTC)
    assert not is_before_lock(lock.WAVE2_OPEN_UTC)
    # Between the first lock and the wave's opening a sitting is in neither wave.
    between = datetime(2026, 9, 29, 12, 0, 0, tzinfo=UTC)
    assert not is_before_lock(between) and not lock.is_in_wave2(between)
