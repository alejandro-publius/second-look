"""The service worker ships whole. A merge once emptied it and every check stayed green."""

from __future__ import annotations

import re
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


def test_the_ports_content_that_browsers_get_has_no_gold_key() -> None:
    text = (ROOT / "worker" / "src" / "core" / "core_content.json").read_text(encoding="utf-8")
    assert '"gold"' not in text and "test_items" not in text


def test_no_web_file_imports_the_workers_full_content() -> None:
    web = ROOT / "apps" / "web"
    offenders = [
        str(p.relative_to(ROOT))
        for p in [
            *web.glob("app/**/*.ts*"),
            *web.glob("components/**/*.ts*"),
            *web.glob("lib/**/*.ts"),
        ]
        if re.search(
            r"""from\s+["'][^"']*worker/src/content\.json["']""", p.read_text(encoding="utf-8")
        )
    ]
    assert offenders == []
