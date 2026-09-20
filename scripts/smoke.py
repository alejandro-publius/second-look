"""Smoke test against a running stack (compose or deployed).

Proves: the static page paints, the API answers, a database row is written and read back.
Set WEB_ORIGIN and API_ORIGIN to point elsewhere."""

from __future__ import annotations

import os
import sys
import time

import httpx

WEB = os.environ.get("WEB_ORIGIN", "http://localhost:3000")
API = os.environ.get("API_ORIGIN", "http://localhost:8000")


def wait(url: str, seconds: int = 90) -> httpx.Response:
    deadline = time.time() + seconds
    last: Exception | None = None
    while time.time() < deadline:
        try:
            r = httpx.get(url, timeout=5)
            if r.status_code < 500:
                return r
        except httpx.HTTPError as e:
            last = e
        time.sleep(2)
    raise SystemExit(f"smoke: {url} not up after {seconds}s: {last}")


def main() -> int:
    t0 = time.time()
    page = wait(f"{WEB}/")
    first_paint_ms = int((time.time() - t0) * 1000)
    assert page.status_code == 200 and "Second Look" in page.text, "landing page did not render"
    health = wait(f"{API}/health")
    assert health.json() == {"status": "ok"}, "api health failed"
    a = httpx.post(f"{API}/api/skeleton/ping", timeout=10).json()["rows"]
    b = httpx.post(f"{API}/api/skeleton/ping", timeout=10).json()["rows"]
    assert b == a + 1, f"database round trip failed: {a} then {b}"
    print(f"smoke: landing 200 in {first_paint_ms} ms, api health ok, db rows {a} then {b}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
