"""The real Open-Meteo fetch on a stubbed network: one GET, one retry, any failure is unknown."""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx
import yaml
from hypothesis import given, settings
from hypothesis import strategies as st

from core.followups import SiteContext, select_followups
from core.rainfall import (
    FETCH_RETRIES,
    FETCH_TIMEOUT_SECONDS,
    OPEN_METEO_URL,
    UNKNOWN,
    RainStatus,
    _default_fetch,
    build_url,
    cache_key,
    dry_status,
)

ROOT = Path(__file__).resolve().parents[2]
TABLE: dict[str, Any] = yaml.safe_load((ROOT / "content" / "followups.yaml").read_text("utf-8"))
FORM_ITEMS: list[dict[str, Any]] = yaml.safe_load(
    (ROOT / "content" / "form.yaml").read_text("utf-8")
)["items"]

LAT, LON = 37.8719, -122.2585
NOW = datetime(2026, 9, 20, 14, 30, tzinfo=UTC)
START = datetime(2026, 9, 16, 0, 0, tzinfo=UTC)
HOURS = 120
PIPE_SEEN: dict[str, str | float | list[str]] = {"draining_pipes": "present"}
TRIES = 1 + FETCH_RETRIES
FAILURES = (
    "server_error",
    "not_found",
    "rate_limited",
    "not_json",
    "json_list",
    "json_null",
    "read_timeout",
    "connect_timeout",
    "connect_error",
)


def payload(rain: dict[datetime, float] | None = None) -> dict[str, Any]:
    """An Open-Meteo body in the confirmed shape: 120 hours from 00:00 UTC four days ago."""
    times: list[str] = []
    values: list[float] = []
    for i in range(HOURS):
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


def failure(kind: str) -> httpx.Response | Exception:
    """One bad answer from the network, as a response or as the error httpx would raise."""
    if kind == "server_error":
        return httpx.Response(503)
    if kind == "not_found":
        return httpx.Response(404)
    if kind == "rate_limited":
        return httpx.Response(429)
    if kind == "not_json":
        return httpx.Response(200, content=b"<html>busy</html>")
    if kind == "json_list":
        return httpx.Response(200, json=[payload()])
    if kind == "json_null":
        return httpx.Response(200, content=b"null")
    if kind == "read_timeout":
        return httpx.ReadTimeout("read took longer than 5 seconds")
    if kind == "connect_timeout":
        return httpx.ConnectTimeout("connect took longer than 5 seconds")
    if kind == "connect_error":
        return httpx.ConnectError("no route to host")
    raise AssertionError(f"unknown failure kind {kind}")


def followup_ids(status: RainStatus) -> list[str]:
    """The follow-ups code would pick for a pipe sighting, with rain passed on as the API does."""
    site = SiteContext(
        rain=status.status,
        dry_days=status.dry_days,
        mm_in_window=status.mm_in_window,
    )
    chosen = select_followups(PIPE_SEEN, site, None, [], TABLE, form_items=FORM_ITEMS)
    return [c.rule_id for c in chosen]


@pytest.fixture
def open_meteo() -> Iterator[respx.Route]:
    """The Open-Meteo forecast route. Any other request fails the call, so nothing leaves."""
    with respx.mock(assert_all_called=False) as router:
        yield router.get(OPEN_METEO_URL)


def test_default_fetch_sends_one_get_to_open_meteo_with_the_built_query(
    open_meteo: respx.Route,
) -> None:
    body = payload()
    open_meteo.mock(return_value=httpx.Response(200, json=body))

    assert _default_fetch(build_url(LAT, LON)) == body

    assert open_meteo.call_count == 1
    request = open_meteo.calls.last.request
    assert request.method == "GET"
    assert request.url.scheme == "https"
    assert request.url.host == "api.open-meteo.com"
    assert request.url.path == "/v1/forecast"
    assert dict(request.url.params) == {
        "latitude": "37.8719",
        "longitude": "-122.2585",
        "hourly": "precipitation",
        "past_days": "4",
        "forecast_days": "1",
        "timezone": "UTC",
    }


def test_default_fetch_waits_five_seconds_at_most_for_every_stage(
    open_meteo: respx.Route,
) -> None:
    open_meteo.mock(return_value=httpx.Response(200, json=payload()))
    _default_fetch(build_url(LAT, LON))
    timeout = open_meteo.calls.last.request.extensions["timeout"]
    assert FETCH_TIMEOUT_SECONDS == 5.0
    assert timeout == {"connect": 5.0, "read": 5.0, "write": 5.0, "pool": 5.0}


@pytest.mark.parametrize("code", [404, 429, 500, 503])
def test_an_http_error_is_retried_once_then_raised(open_meteo: respx.Route, code: int) -> None:
    open_meteo.mock(return_value=httpx.Response(code))
    with pytest.raises(httpx.HTTPStatusError) as caught:
        _default_fetch(build_url(LAT, LON))
    assert caught.value.response.status_code == code
    assert open_meteo.call_count == TRIES == 2


def test_a_body_that_is_not_json_is_retried_once_then_raised(open_meteo: respx.Route) -> None:
    open_meteo.mock(return_value=httpx.Response(200, content=b"<html>busy</html>"))
    with pytest.raises(json.JSONDecodeError):
        _default_fetch(build_url(LAT, LON))
    assert open_meteo.call_count == 2


@pytest.mark.parametrize("body", [b"[1, 2]", b'"rain"', b"3.5", b"null", b"true"])
def test_json_that_is_not_an_object_is_refused(open_meteo: respx.Route, body: bytes) -> None:
    open_meteo.mock(return_value=httpx.Response(200, content=body))
    with pytest.raises(ValueError, match="payload is not an object"):
        _default_fetch(build_url(LAT, LON))
    assert open_meteo.call_count == 2


@pytest.mark.parametrize(
    "error",
    [httpx.ReadTimeout("slow read"), httpx.ConnectTimeout("slow connect")],
    ids=["read", "connect"],
)
def test_a_timeout_is_retried_once_then_raised(
    open_meteo: respx.Route, error: httpx.TimeoutException
) -> None:
    open_meteo.mock(side_effect=error)
    with pytest.raises(httpx.TimeoutException):
        _default_fetch(build_url(LAT, LON))
    assert open_meteo.call_count == 2


def test_the_retry_can_rescue_a_first_failure(open_meteo: respx.Route) -> None:
    body = payload()
    open_meteo.mock(
        side_effect=[httpx.ConnectTimeout("slow connect"), httpx.Response(200, json=body)]
    )
    assert _default_fetch(build_url(LAT, LON)) == body
    assert open_meteo.call_count == 2


def test_when_both_tries_fail_the_second_failure_is_the_one_raised(
    open_meteo: respx.Route,
) -> None:
    open_meteo.mock(side_effect=[httpx.Response(500), httpx.ReadTimeout("slow read")])
    with pytest.raises(httpx.ReadTimeout, match="slow read"):
        _default_fetch(build_url(LAT, LON))
    assert open_meteo.call_count == 2


def test_a_dry_spell_over_the_network_is_dry_and_can_ask_the_dry_pipe_question(
    open_meteo: respx.Route,
) -> None:
    open_meteo.mock(return_value=httpx.Response(200, json=payload()))
    status = dry_status(LAT, LON, NOW)
    assert status == RainStatus(status="dry", mm_in_window=0.0, dry_days=4, source="open-meteo")
    assert followup_ids(status) == ["dry_pipe"]
    assert str(open_meteo.calls.last.request.url) == build_url(LAT, LON)


def test_recent_rain_over_the_network_is_wet_and_skips_the_dry_pipe_question(
    open_meteo: respx.Route,
) -> None:
    ten_hours_ago = NOW.replace(minute=0) - timedelta(hours=10)
    open_meteo.mock(return_value=httpx.Response(200, json=payload({ten_hours_ago: 5.0})))
    status = dry_status(LAT, LON, NOW)
    assert status == RainStatus(status="wet", mm_in_window=5.0, dry_days=0, source="open-meteo")
    assert "dry_pipe" not in followup_ids(status)


def test_a_fetched_payload_is_cached_for_the_hour_so_the_network_is_asked_once(
    open_meteo: respx.Route,
) -> None:
    body = payload()
    open_meteo.mock(return_value=httpx.Response(200, json=body))
    cache: dict[str, tuple[datetime, dict[Any, Any]]] = {}

    first = dry_status(LAT, LON, NOW, cache=cache)
    later = dry_status(LAT, LON, NOW + timedelta(minutes=20), cache=cache)

    assert first == later
    assert first.status == "dry"
    assert open_meteo.call_count == 1
    assert cache == {cache_key(LAT, LON, NOW): (NOW, body)}


@pytest.mark.parametrize("kind", FAILURES)
def test_every_network_failure_is_unknown_and_never_asks_the_dry_pipe_question(
    open_meteo: respx.Route, kind: str
) -> None:
    open_meteo.mock(side_effect=[failure(kind), failure(kind)])
    cache: dict[str, tuple[datetime, dict[Any, Any]]] = {}

    status = dry_status(LAT, LON, NOW, cache=cache)

    assert status == UNKNOWN
    assert status.status == "unknown"
    assert status.dry_days is None
    assert status.mm_in_window is None
    assert "dry_pipe" not in followup_ids(status)
    assert open_meteo.call_count == 2
    assert cache == {}


@settings(max_examples=60, deadline=None, database=None)
@given(first=st.sampled_from(FAILURES), second=st.sampled_from(FAILURES))
def test_any_two_failures_in_a_row_are_unknown_after_exactly_two_requests(
    first: str, second: str
) -> None:
    with respx.mock(assert_all_called=True) as router:
        route = router.get(OPEN_METEO_URL).mock(side_effect=[failure(first), failure(second)])
        status = dry_status(LAT, LON, NOW)
        assert route.call_count == 2
    assert status == UNKNOWN
    assert "dry_pipe" not in followup_ids(status)


@settings(max_examples=30, deadline=None, database=None)
@given(first=st.sampled_from(FAILURES))
def test_any_single_failure_is_rescued_by_the_one_retry(first: str) -> None:
    with respx.mock(assert_all_called=True) as router:
        route = router.get(OPEN_METEO_URL).mock(
            side_effect=[failure(first), httpx.Response(200, json=payload())]
        )
        status = dry_status(LAT, LON, NOW)
        assert route.call_count == 2
    assert status.status == "dry"
    assert status.dry_days == 4
