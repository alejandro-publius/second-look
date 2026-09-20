"""Rainfall with canned payloads: dry, wet, the 2.5 mm boundary, malformed, exception, cache."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from core import rainfall
from core.rainfall import UNKNOWN, RainStatus, build_url, cache_key, dry_status

LAT, LON = 37.8719, -122.2585
NOW = datetime(2026, 9, 20, 14, 30, tzinfo=UTC)
START = datetime(2026, 9, 16, 0, 0, tzinfo=UTC)
HOURS = 120


def payload(rain: dict[datetime, float] | None = None, *, count: int = HOURS) -> dict[str, Any]:
    times: list[str] = []
    values: list[float] = []
    for i in range(count):
        t = START + timedelta(hours=i)
        times.append(t.strftime("%Y-%m-%dT%H:%M"))
        values.append((rain or {}).get(t, 0.0))
    return {
        "latitude": 37.875,
        "longitude": -122.25,
        "utc_offset_seconds": 0,
        "timezone": "GMT",
        "hourly_units": {"time": "iso8601", "precipitation": "mm"},
        "hourly": {"time": times, "precipitation": values},
    }


class Spy:
    def __init__(self, result: Any = None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.urls: list[str] = []

    def __call__(self, url: str) -> dict[str, Any]:
        self.urls.append(url)
        if self.error is not None:
            raise self.error
        return self.result


def hour(hours_before_now: int) -> datetime:
    """The hour bucket ending this many whole hours before the top of the current hour."""
    return NOW.replace(minute=0) - timedelta(hours=hours_before_now)


def test_build_url_covers_the_past_window_in_utc() -> None:
    url = build_url(LAT, LON)
    assert url.startswith("https://api.open-meteo.com/v1/forecast?")
    for part in (
        "latitude=37.8719",
        "longitude=-122.2585",
        "hourly=precipitation",
        "past_days=4",
        "forecast_days=1",
        "timezone=UTC",
    ):
        assert part in url


def test_dry_payload_gives_dry_with_four_dry_days() -> None:
    spy = Spy(payload())
    status = dry_status(LAT, LON, NOW, fetch=spy)
    assert status == RainStatus(status="dry", mm_in_window=0.0, dry_days=4, source="open-meteo")
    assert spy.urls == [build_url(LAT, LON)]


def test_wet_payload_gives_wet_with_no_dry_days() -> None:
    status = dry_status(LAT, LON, NOW, fetch=Spy(payload({hour(10): 5.0})))
    assert status == RainStatus(status="wet", mm_in_window=5.0, dry_days=0, source="open-meteo")


def test_exactly_the_threshold_is_dry_and_a_hair_over_is_wet() -> None:
    at_line = dry_status(LAT, LON, NOW, fetch=Spy(payload({hour(10): 2.5})))
    assert at_line.status == "dry" and at_line.mm_in_window == 2.5
    spread = payload({hour(h): 0.5 for h in (5, 15, 25, 35, 45)})
    assert dry_status(LAT, LON, NOW, fetch=Spy(spread)).status == "dry"
    over = dry_status(LAT, LON, NOW, fetch=Spy(payload({hour(10): 2.6})))
    assert over.status == "wet" and over.mm_in_window == 2.6


def test_window_edges_follow_hour_buckets_ending_inside_the_window() -> None:
    outside = payload(
        {NOW - timedelta(hours=72, minutes=30): 20.0}
    )  # bucket ending 14:00, 3 days ago
    assert dry_status(LAT, LON, NOW, fetch=Spy(outside)).status == "dry"
    inside = payload(
        {NOW - timedelta(hours=71, minutes=30): 20.0}
    )  # bucket ending 15:00, 3 days ago
    assert dry_status(LAT, LON, NOW, fetch=Spy(inside)).status == "wet"


def test_future_forecast_hours_are_ignored() -> None:
    status = dry_status(LAT, LON, NOW, fetch=Spy(payload({hour(-3): 30.0})))
    assert status.status == "dry" and status.mm_in_window == 0.0


def test_dry_days_stop_at_the_first_day_with_a_wet_hour() -> None:
    status = dry_status(LAT, LON, NOW, fetch=Spy(payload({hour(30): 0.5})))
    assert status.status == "dry"
    assert status.dry_days == 1
    two_days = dry_status(LAT, LON, NOW, fetch=Spy(payload({hour(60): 0.3})))
    assert two_days.dry_days == 2


def test_a_tenth_of_a_millimetre_is_still_a_dry_hour_but_more_is_not() -> None:
    assert dry_status(LAT, LON, NOW, fetch=Spy(payload({hour(5): 0.1}))).dry_days == 4
    drizzle = dry_status(LAT, LON, NOW, fetch=Spy(payload({hour(5): 0.2})))
    assert drizzle.status == "dry" and drizzle.dry_days == 0


def test_thresholds_are_configurable() -> None:
    rain = payload({hour(30): 2.0})
    assert dry_status(LAT, LON, NOW, fetch=Spy(rain), dry_mm=1.0).status == "wet"
    short = dry_status(LAT, LON, NOW, fetch=Spy(rain), window_hours=24)
    assert short.status == "dry" and short.mm_in_window == 0.0


@pytest.mark.parametrize(
    "bad",
    [
        {},
        {"hourly": None},
        {"hourly": {"time": ["2026-09-20T14:00"]}},
        {"hourly": {"time": ["2026-09-20T14:00"], "precipitation": "x"}},
        {"hourly": {"time": ["2026-09-20T14:00", "2026-09-20T15:00"], "precipitation": [0.0]}},
        {"hourly": {"time": ["not a time"], "precipitation": [0.0]}},
        {"hourly": {"time": [14], "precipitation": [0.0]}},
        [],
        None,
        "text",
    ],
)
def test_malformed_payload_is_unknown(bad: Any) -> None:
    assert dry_status(LAT, LON, NOW, fetch=Spy(bad)) == UNKNOWN


def test_null_negative_or_boolean_values_in_the_window_are_unknown() -> None:
    for value in (None, -1.0, True, float("nan")):
        broken = payload()
        broken["hourly"]["precipitation"][-40] = value
        assert dry_status(LAT, LON, NOW, fetch=Spy(broken)) == UNKNOWN


def test_short_coverage_is_unknown() -> None:
    assert dry_status(LAT, LON, NOW, fetch=Spy(payload(count=10))) == UNKNOWN


def test_fetch_exception_is_unknown_and_never_raises() -> None:
    assert dry_status(LAT, LON, NOW, fetch=Spy(error=RuntimeError("boom"))) == UNKNOWN
    assert dry_status(LAT, LON, NOW, fetch=Spy(error=TimeoutError())) == UNKNOWN
    assert UNKNOWN.source == "unknown" and UNKNOWN.mm_in_window is None and UNKNOWN.dry_days is None


def test_bad_coordinates_are_unknown_without_a_fetch() -> None:
    spy = Spy(payload())
    assert dry_status(95.0, LON, NOW, fetch=spy) == UNKNOWN
    assert dry_status(LAT, 181.0, NOW, fetch=spy) == UNKNOWN
    assert dry_status(float("nan"), LON, NOW, fetch=spy) == UNKNOWN
    assert spy.urls == []


def test_cache_hit_skips_the_fetch() -> None:
    spy = Spy(payload({hour(10): 5.0}))
    cache: dict[str, tuple[datetime, dict]] = {cache_key(LAT, LON, NOW): (NOW, payload())}
    status = dry_status(LAT, LON, NOW, fetch=spy, cache=cache)
    assert status.status == "dry"
    assert spy.urls == []


def test_cache_is_filled_after_a_fetch_and_reused_within_the_hour() -> None:
    spy = Spy(payload())
    cache: dict[str, tuple[datetime, dict]] = {}
    dry_status(LAT, LON, NOW, fetch=spy, cache=cache)
    dry_status(LAT + 0.002, LON - 0.001, NOW + timedelta(minutes=20), fetch=spy, cache=cache)
    assert len(spy.urls) == 1
    assert list(cache) == ["37.87,-122.26,2026-09-20T14"]
    dry_status(LAT, LON, NOW + timedelta(hours=1), fetch=spy, cache=cache)
    assert len(spy.urls) == 2


def test_cache_is_not_filled_on_failure() -> None:
    cache: dict[str, tuple[datetime, dict]] = {}
    dry_status(LAT, LON, NOW, fetch=Spy(error=RuntimeError()), cache=cache)
    dry_status(LAT, LON, NOW, fetch=Spy("garbage"), cache=cache)
    assert cache == {}


def test_naive_now_is_treated_as_utc() -> None:
    status = dry_status(LAT, LON, NOW.replace(tzinfo=None), fetch=Spy(payload({hour(10): 5.0})))
    assert status.status == "wet"


def test_default_fetch_is_used_only_when_no_fetch_is_given(monkeypatch: pytest.MonkeyPatch) -> None:
    spy = Spy(payload())
    monkeypatch.setattr(rainfall, "_default_fetch", spy)
    assert dry_status(LAT, LON, NOW).status == "dry"
    assert len(spy.urls) == 1
    assert rainfall.FETCH_TIMEOUT_SECONDS == 5.0
    assert rainfall.FETCH_RETRIES == 1


def test_attribution_is_in_the_module_docstring() -> None:
    doc = rainfall.__doc__ or ""
    assert "Weather data by Open-Meteo.com, CC BY 4.0" in doc
    assert "https://open-meteo.com/en/terms" in doc
