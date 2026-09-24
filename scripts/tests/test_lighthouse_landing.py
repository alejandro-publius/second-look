"""The server scripts/lighthouse_landing.py measures behind: it must serve an export the way
Cloudflare Pages does, or the landing page's scores describe a different site."""

from __future__ import annotations

import json
import socket
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
    (tmp_path / "secret.txt").write_text("outside the site")
    root = tmp_path / "site"
    root.mkdir()
    (root / "index.html").write_text("<h1>landing</h1>")
    (root / "about.html").write_text("<h1>about</h1>")
    (root / "404.html").write_text("<h1>not here</h1>")
    (root / "sw.js").write_text("self.x = 1;")
    (root / "_headers").write_text(HEADERS)
    return root


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
    assert (site.parent / "secret.txt").is_file()
    assert ll.file_for(site, "/../secret.txt") is None
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
            plain = client.get("/", headers={"Accept-Encoding": "identity"})
            assert "content-encoding" not in plain.headers
            assert plain.content == b"<h1>landing</h1>"
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
        # httpx never reads a body after HEAD, so read the raw reply: headers and nothing more.
        host, port = url.removeprefix("http://").rstrip("/").split(":")
        with socket.create_connection((host, int(port))) as raw_socket:
            raw_socket.sendall(b"HEAD /about HTTP/1.0\r\n\r\n")
            reply = b"".join(iter(lambda: raw_socket.recv(4096), b""))
        assert reply.startswith(b"HTTP/1.0 200") and reply.endswith(b"\r\n\r\n")
    finally:
        server.shutdown()


def test_the_reported_run_is_the_one_with_the_median_performance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scores = iter([98, 93, 97])
    monkeypatch.setattr(
        ll, "one_run", lambda url, report: {"scores": {"performance": next(scores)}}
    )
    runs, median = ll.measure("http://x/", 3, tmp_path)
    assert [r["scores"]["performance"] for r in runs] == [98, 93, 97]
    assert median["scores"]["performance"] == 97


def test_the_committed_result_is_the_shape_the_done_check_reads() -> None:
    doc = json.loads((ll.OUT).read_text(encoding="utf-8"))
    scores = doc["median"]["scores"]
    assert set(ll.CATEGORIES) <= set(scores)
    assert doc["median"] in doc["runs"]
    assert doc["target"] and doc["commit"]
    assert doc["median"]["form_factor"] == "mobile"
    assert doc["median"]["throttling_method"] == "simulate"
