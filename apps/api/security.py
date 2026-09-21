"""Rate limit, log filters, response headers and constant time secret checks.

Nothing in here writes to disk. The rate limit lives in process memory, keyed by a salted hash
of the client address, and is gone when the process stops. Production runs uvicorn with
--no-access-log; the filters below are the second line of defence and the one tests exercise.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import re
import secrets
import threading
import time
from collections import deque
from collections.abc import Callable

from fastapi import HTTPException, Request
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

log = logging.getLogger("apps.api")

# Dotted IPv4, bracketed IPv6 and the Starlette test client's fixed address.
ADDRESS_RE = re.compile(
    r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])|\[[0-9a-fA-F:.]+\]|testclient", re.IGNORECASE
)
REDACTED = "[address removed]"


class DropAccessLog(logging.Filter):
    """uvicorn access lines start with the client address, so none of them may pass."""

    def filter(self, record: logging.LogRecord) -> bool:
        return False


class RedactAddresses(logging.Filter):
    """Replaces anything that looks like a client address in any other log line."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        cleaned = ADDRESS_RE.sub(REDACTED, message)
        if cleaned != message:
            record.msg = cleaned
            record.args = ()
        return True


def install_log_filters() -> None:
    """Idempotent. Call once at import of the app and again in tests after logging is reset."""
    access = logging.getLogger("uvicorn.access")
    if not any(isinstance(f, DropAccessLog) for f in access.filters):
        access.addFilter(DropAccessLog())
    for name in ("", "uvicorn", "uvicorn.error", "apps.api"):
        logger = logging.getLogger(name)
        if not any(isinstance(f, RedactAddresses) for f in logger.filters):
            logger.addFilter(RedactAddresses())
        for handler in logger.handlers:
            if not any(isinstance(f, RedactAddresses) for f in handler.filters):
                handler.addFilter(RedactAddresses())


class RateLimiter:
    """Sliding window per client address. limit hits per window_seconds, then 429."""

    def __init__(self, limit: int, window_seconds: float, clock: Callable[[], float] | None = None):
        self.limit = limit
        self.window = window_seconds
        self._clock = clock or time.monotonic
        self._salt = secrets.token_bytes(16)
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def _key(self, address: str) -> str:
        return hashlib.sha256(self._salt + address.encode()).hexdigest()[:24]

    def allow(self, address: str) -> bool:
        now = self._clock()
        key = self._key(address)
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and hits[0] <= now - self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                return False
            hits.append(now)
            if len(self._hits) > 10_000:
                self._prune(now)
            return True

    def _prune(self, now: float) -> None:
        stale = [k for k, v in self._hits.items() if not v or v[-1] <= now - self.window]
        for k in stale:
            del self._hits[k]

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


STUDY_LIMIT = RateLimiter(limit=60, window_seconds=10)
DEMO_LIMIT = RateLimiter(limit=30, window_seconds=10)
READ_LIMIT = RateLimiter(limit=60, window_seconds=10)
UPLOAD_LIMIT = RateLimiter(limit=12, window_seconds=60)
ALL_LIMITERS = (STUDY_LIMIT, DEMO_LIMIT, READ_LIMIT, UPLOAD_LIMIT)


def reset_rate_limits() -> None:
    for limiter in ALL_LIMITERS:
        limiter.reset()


def client_address(request: Request) -> str:
    """The address uvicorn saw. Behind a proxy run uvicorn with --proxy-headers so this is the
    visitor and not the proxy. Never stored, never logged."""
    return request.client.host if request.client else "unknown"


def rate_limited(limiter: RateLimiter) -> Callable[[Request], None]:
    def dependency(request: Request) -> None:
        if not limiter.allow(client_address(request)):
            raise HTTPException(
                status_code=429,
                detail="Too many requests from this connection. Wait a few seconds and try again.",
            )

    return dependency


def same_secret(given: str | None, expected: str) -> bool:
    """Constant time compare. A missing or empty value never matches."""
    if not given:
        return False
    return hmac.compare_digest(given.encode(), expected.encode())


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class SecurityHeaders:
    """Every response, including CORS preflights and errors, carries these headers.
    The API serves data, not pages, so the browser may load nothing from it."""

    HEADERS = {
        "Content-Security-Policy": "default-src 'none'",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
    }

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in self.HEADERS.items():
                    headers[name] = value
            await send(message)

        await self.app(scope, receive, send_with_headers)
