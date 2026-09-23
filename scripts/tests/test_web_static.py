"""The service worker ships whole. A merge once emptied it and every check stayed green."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SW = ROOT / "apps" / "web" / "public" / "sw.js"


def test_the_service_worker_is_not_empty_and_still_precaches() -> None:
    text = SW.read_text(encoding="utf-8")
    assert len(text) > 1000, "apps/web/public/sw.js is empty or cut short"
    assert "precache.json" in text
    assert 'addEventListener("fetch"' in text


def test_walk_clips_bypass_the_service_worker() -> None:
    assert 'url.pathname.startsWith("/walks/")' in SW.read_text(encoding="utf-8")
