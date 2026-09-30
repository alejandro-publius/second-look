"""Rate limit, logs without addresses, CORS, security headers."""

from __future__ import annotations

import logging

from apps.api.security import (
    STUDY_LIMIT,
    RateLimiter,
    RedactAddresses,
    install_log_filters,
    reset_rate_limits,
)
from apps.api.tests.conftest import SESSION_BODY, freeze_now, full_session
from core.lock import JUDGE_MODE_OPENS_UTC


class ListHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.lines.append(self.format(record))


def test_rate_limiter_is_a_sliding_window_in_memory():
    clock = [1000.0]
    limiter = RateLimiter(limit=3, window_seconds=10, clock=lambda: clock[0])
    assert [limiter.allow("1.2.3.4") for _ in range(4)] == [True, True, True, False]
    assert limiter.allow("5.6.7.8") is True  # another address has its own budget
    clock[0] += 10.1
    assert limiter.allow("1.2.3.4") is True
    # The raw address is not kept, only a salted hash of it.
    assert "1.2.3.4" not in repr(limiter.__dict__)


def test_too_many_requests_get_429_then_recover(client, monkeypatch):
    monkeypatch.setattr(STUDY_LIMIT, "limit", 3)
    reset_rate_limits()
    codes = [client.post("/api/test/session", json=SESSION_BODY).status_code for _ in range(4)]
    assert codes == [200, 200, 200, 429]
    detail = client.post("/api/test/session", json=SESSION_BODY).json()["detail"]
    assert "Wait a few seconds" in detail
    reset_rate_limits()
    assert client.post("/api/test/session", json=SESSION_BODY).status_code == 200


def test_demo_route_is_rate_limited_separately(client, monkeypatch):
    from apps.api.security import DEMO_LIMIT

    monkeypatch.setattr(DEMO_LIMIT, "limit", 2)
    reset_rate_limits()
    freeze_now(JUDGE_MODE_OPENS_UTC)  # judge mode is open from the second lock on
    codes = [
        client.post("/api/demo/answer", json={"item_id": "t01", "answer": "yes"}).status_code
        for _ in range(3)
    ]
    assert codes == [200, 200, 429]
    assert client.post("/api/test/session", json=SESSION_BODY).status_code == 200


def test_full_session_leaves_no_client_address_in_any_log_line(client):
    handler = ListHandler()
    handler.setFormatter(logging.Formatter("%(name)s %(levelname)s %(message)s"))
    root = logging.getLogger()
    old_level = root.level
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error", "apps.api"):
        logging.getLogger(name).setLevel(logging.DEBUG)
    install_log_filters()
    try:
        full_session(client, keep_score=True)
        client.get("/api/test/counts")
        client.post("/api/demo/answer", json={"item_id": "t01", "answer": "yes"})
        # What uvicorn would log with access logging on. The filter must drop it.
        logging.getLogger("uvicorn.access").info(
            '%s - "%s %s HTTP/%s" %d', "testclient:50000", "POST", "/api/test/session", "1.1", 200
        )
        # A stray address in any other logger must come out redacted.
        logging.getLogger("uvicorn.error").warning("peer 203.0.113.9 closed the connection")
        logging.getLogger("apps.api").info("control line without an address")
    finally:
        root.removeHandler(handler)
        root.setLevel(old_level)
    assert any("control line" in line for line in handler.lines), handler.lines
    assert any("[address removed] closed" in line for line in handler.lines), handler.lines
    for line in handler.lines:
        assert "testclient" not in line.lower(), line
        assert "203.0.113.9" not in line, line
        assert not RedactAddresses.__doc__ or "127.0.0.1" not in line, line


def test_cors_allows_only_the_public_web_origin(client):
    ok = client.options(
        "/api/test/session",
        headers={
            "Origin": "http://web.test",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert ok.status_code == 200
    assert ok.headers["access-control-allow-origin"] == "http://web.test"
    other = client.get("/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in other.headers
    same = client.get("/health", headers={"Origin": "http://web.test"})
    assert same.headers["access-control-allow-origin"] == "http://web.test"


def test_every_response_carries_csp_and_nosniff(client):
    responses = [
        client.get("/health"),
        client.get("/api/content/hash"),
        client.get("/api/test/export?token=wrong"),
        client.get("/nope"),
        client.post("/api/test/response", json={}),
        client.options(
            "/api/test/session",
            headers={"Origin": "http://web.test", "Access-Control-Request-Method": "POST"},
        ),
    ]
    for r in responses:
        assert r.headers["content-security-policy"] == "default-src 'none'", r.url
        assert r.headers["x-content-type-options"] == "nosniff", r.url
        assert r.headers["referrer-policy"] == "no-referrer", r.url
