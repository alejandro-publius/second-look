"""Rainfall for the dry pipe rule, from Open-Meteo. Fails closed to unknown (Update 02 section 10).

Weather data by Open-Meteo.com, CC BY 4.0. Terms: https://open-meteo.com/en/terms
Attribution line for docs/THIRD_PARTY.md: "Weather data by Open-Meteo.com, CC BY 4.0".

The only network call in core/ lives in _default_fetch, and only when the caller passes no fetch
function. Tests always inject a fetch. The cache is an injected mapping keyed by the rounded
coordinates (2 decimals) and the UTC hour.

Payload shape, confirmed with one request on 2026-09-20 to
https://api.open-meteo.com/v1/forecast?latitude=37.87&longitude=-122.26&hourly=precipitation
&past_days=4&forecast_days=1&timezone=UTC :
  top keys: elevation, generationtime_ms, hourly, hourly_units, latitude, longitude, timezone,
            timezone_abbreviation, utc_offset_seconds
  hourly keys: time (list of "YYYY-MM-DDTHH:MM" strings), precipitation (list of floats)
  hourly_units: {"time": "iso8601", "precipitation": "mm"}
  120 hours: 4 past days plus today, from 00:00 UTC four days ago.
Open-Meteo documents hourly precipitation as the sum of the preceding hour, so the value stamped
14:00 covers 13:00 to 14:00.
"""

from __future__ import annotations

import math
from collections.abc import Callable, MutableMapping
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from urllib.parse import urlencode

from core.records import Frozen

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
SOURCE_OPEN_METEO = "open-meteo"
SOURCE_UNKNOWN = "unknown"
PAST_DAYS = 4
FORECAST_DAYS = 1
DEFAULT_DRY_MM = 2.5
DEFAULT_WINDOW_HOURS = 72
DRY_HOUR_MAX_MM = 0.1
FETCH_TIMEOUT_SECONDS = 5.0
FETCH_RETRIES = 1
HOURS_PER_DAY = 24
MM_DECIMALS = 2

RainStatusValue = Literal["dry", "wet", "unknown"]


class RainStatus(Frozen):
    """What code knows about recent rain at a spot."""

    status: RainStatusValue
    mm_in_window: float | None
    dry_days: int | None
    source: str


UNKNOWN = RainStatus(status="unknown", mm_in_window=None, dry_days=None, source=SOURCE_UNKNOWN)


def build_url(latitude: float, longitude: float) -> str:
    """The Open-Meteo request for hourly precipitation over the past days, in UTC."""
    query = urlencode(
        {
            "latitude": f"{latitude:.4f}",
            "longitude": f"{longitude:.4f}",
            "hourly": "precipitation",
            "past_days": PAST_DAYS,
            "forecast_days": FORECAST_DAYS,
            "timezone": "UTC",
        }
    )
    return f"{OPEN_METEO_URL}?{query}"


def cache_key(latitude: float, longitude: float, now: datetime) -> str:
    """Rounded coordinates (2 decimals) plus the UTC hour."""
    return f"{latitude:.2f},{longitude:.2f},{now.astimezone(UTC):%Y-%m-%dT%H}"


def _default_fetch(url: str) -> dict[str, Any]:
    """GET the url with a 5 second timeout and exactly one retry. Never called in tests."""
    import httpx

    last: Exception | None = None
    for _attempt in range(1 + FETCH_RETRIES):
        try:
            response = httpx.get(url, timeout=FETCH_TIMEOUT_SECONDS)
            response.raise_for_status()
            body = response.json()
            if not isinstance(body, dict):
                raise ValueError("payload is not an object")
            return body
        except Exception as exc:  # retried once, then the caller sees unknown
            last = exc
    assert last is not None
    raise last


def _as_utc(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC)


def _parse_hour(text: object) -> datetime:
    if not isinstance(text, str):
        raise ValueError("time is not text")
    return datetime.fromisoformat(text).replace(tzinfo=UTC)


def _hours(payload: object) -> list[tuple[datetime, float]]:
    """(hour end, mm) pairs from the payload. Raises on any malformed piece."""
    if not isinstance(payload, dict):
        raise ValueError("payload is not an object")
    hourly = payload["hourly"]
    if not isinstance(hourly, dict):
        raise ValueError("hourly is not an object")
    times = hourly["time"]
    values = hourly["precipitation"]
    if not isinstance(times, list) or not isinstance(values, list) or len(times) != len(values):
        raise ValueError("time and precipitation lists do not line up")
    out: list[tuple[datetime, float]] = []
    for text, value in zip(times, values, strict=True):
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError("precipitation is not a number")
        mm = float(value)
        if not math.isfinite(mm) or mm < 0.0:
            raise ValueError("precipitation is not a finite non-negative number")
        out.append((_parse_hour(text), mm))
    return out


def _window(
    hours: list[tuple[datetime, float]], start: datetime, end: datetime
) -> list[float] | None:
    """Values for hour buckets ending in (start, end], or None when the span is not covered."""
    picked = [mm for hour_end, mm in hours if start < hour_end <= end]
    needed = int((end - start) / timedelta(hours=1))
    if len(picked) < needed:
        return None
    return picked


def _dry_days(hours: list[tuple[datetime, float]], now: datetime) -> int:
    """Whole days back from now with no hour above DRY_HOUR_MAX_MM, stopping at the first wet or
    uncovered day."""
    days = 0
    while True:
        end = now - timedelta(hours=HOURS_PER_DAY * days)
        start = end - timedelta(hours=HOURS_PER_DAY)
        values = _window(hours, start, end)
        if values is None or any(mm > DRY_HOUR_MAX_MM for mm in values):
            return days
        days += 1


def _status_from_payload(
    payload: object, now: datetime, dry_mm: float, window_hours: int
) -> RainStatus:
    hours = _hours(payload)
    values = _window(hours, now - timedelta(hours=window_hours), now)
    if values is None:
        return UNKNOWN
    total = round(sum(values), MM_DECIMALS)
    status: RainStatusValue = "dry" if total <= dry_mm else "wet"
    return RainStatus(
        status=status,
        mm_in_window=total,
        dry_days=_dry_days(hours, now),
        source=SOURCE_OPEN_METEO,
    )


def _coordinates_ok(latitude: float, longitude: float) -> bool:
    return (
        math.isfinite(latitude)
        and math.isfinite(longitude)
        and -90.0 <= latitude <= 90.0
        and -180.0 <= longitude <= 180.0
    )


def dry_status(
    latitude: float,
    longitude: float,
    now: datetime,
    *,
    dry_mm: float = DEFAULT_DRY_MM,
    window_hours: int = DEFAULT_WINDOW_HOURS,
    fetch: Callable[[str], dict] | None = None,
    cache: MutableMapping[str, tuple[datetime, dict]] | None = None,
) -> RainStatus:
    """Open-Meteo hourly precipitation for the window. Timeout and one retry inside fetch.

    Any failure -> unknown.
    """
    try:
        if not _coordinates_ok(latitude, longitude) or window_hours <= 0:
            return UNKNOWN
        now_utc = _as_utc(now)
        key = cache_key(latitude, longitude, now_utc)
        payload: object = None
        if cache is not None and key in cache:
            payload = cache[key][1]
        else:
            payload = (fetch or _default_fetch)(build_url(latitude, longitude))
            if cache is not None and isinstance(payload, dict):
                cache[key] = (now_utc, payload)
        return _status_from_payload(payload, now_utc, dry_mm, window_hours)
    except Exception:  # any failure, of any kind, is unknown
        return UNKNOWN
