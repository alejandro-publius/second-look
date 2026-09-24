"""The server scripts/lighthouse_landing.py measures behind: it must serve an export the way
Cloudflare Pages does, or the landing page's scores describe a different site."""

from __future__ import annotations

import gzip
import json
from pathlib import Path

import httpx
import pytest

from scripts import lighthouse_landing as ll

HEADERS = """# made by build-headers.mjs
/*
  Content-Security-Policy: default-src 'self'
  X-Frame-Options: DENY

/
  Link: </photos/a.avif>; rel=preload; as=image

/sw.js
  Cache-Control: no-cache
"""


@pytest.fixture
def site(tmp_path: Path) -> Path:
    (tmp_path / "index.html").write_text("<h1>landing</h1>")
    (tmp_path / "about.html").write_text("<h1>about</h1>")
    (tmp_path / "404.html").write_text("<h1>not here</h1>")
    (tmp_path / "sw.js").write_text("self.x = 1;")
    (tmp_path / "_headers").write_text(HEADERS)
    return tmp_path


def test_headers_follow_the_rules_of_the_headers_file(site: Path) -> None:
    rules = ll.header_rules(site)
    landing = ll.headers_for("/", rules)
    assert landing["Content-Security-Policy"] == "default-src 'self'"
    assert landing["Link"].startswith("</photos/a.avif>")
    about = ll.headers_for("/about", rules)
    assert "Link" not in about and about["X-Frame-Options"] == "DENY"
    assert ll.headers_for("/sw.js", rules)["Cache-Control"] == "no-cache"


def test_clean_urls_and_no_way_out_of_the_site(site: Path) -> None:
    assert ll.file_for(site, "/") == site / "index.html"
    assert ll.file_for(site, "/about") == site / "about.html"
    assert ll.file_for(site, "/about?x=1") == site / "about.html"
    assert ll.file_for(site, "/../secret") is None
    assert ll.file_for(site, "/missing") is None


def test_the_server_answers_like_pages(site: Path) -> None:
    server, url = ll.serve(site)
    try:
        with httpx.Client(base_url=url) as client:
            home = client.get("/", headers={"Accept-Encoding": "gzip"})
            assert home.status_code == 200
            assert home.headers["content-encoding"] == "gzip"
            assert home.text == "<h1>landing</h1>"  # httpx undoes the gzip
            assert home.headers["content-security-policy"] == "default-src 'self'"
            assert "link" in home.headers
            raw = client.get("/", headers={"Accept-Encoding": "identity"})
            assert "content-encoding" not in raw.headers
            assert gzip.compress(raw.content) != raw.content
            assert client.get("/about").text == "<h1>about</h1>"
            # The router asks with HEAD; Pages answers it, so a 501 here would be a console
            # error the live site never logs, and a lower best practices score.
            head = client.head("/about")
            assert head.status_code == 200 and head.content == b""
            health = client.get("/health")
            assert health.status_code == 200 and json.loads(health.text) == {"status": "ok"}
            assert client.get("/api/test/session").status_code == 404
            missing = client.get("/nowhere")
            assert missing.status_code == 404 and missing.text == "<h1>not here</h1>"
    finally:
        server.shutdown()


def test_the_committed_result_is_the_shape_the_done_check_reads() -> None:
    doc = json.loads((ll.OUT).read_text(encoding="utf-8"))
    scores = doc["median"]["scores"]
    assert set(ll.CATEGORIES) <= set(scores)
    assert doc["median"] in doc["runs"]
    assert doc["target"] and doc["commit"]
    assert doc["median"]["form_factor"] == "mobile"
    assert doc["median"]["throttling_method"] == "simulate"
