"""Lighthouse on the landing page: four categories, the throttled mobile profile (UPDATE_29 4.3).

  uv run python scripts/lighthouse_landing.py --build      export the site the way scripts/deploy.sh
                                                           does, serve it here the way Pages does,
                                                           and measure it
  uv run python scripts/lighthouse_landing.py --dir apps/web/out     measure an export made already
  uv run python scripts/lighthouse_landing.py --url https://second-look-79t.pages.dev/
                                                           measure the live site, after a deploy

Lighthouse's default mobile run is the throttled profile: a mid-range phone, simulated throttling
at 150 ms round trip and 1.6 Mbps down, the CPU slowed four times. Three runs; the run with the
median performance score is the one reported, as scripts/harden_lighthouse.py does, because one
run moves by a few points. Writes results/lighthouse_landing.json, whose median.scores are what
scripts/done_items.py lighthouse-landing reads. The full reports stay outside the repo.

Served like Pages: the static export with the headers of its own _headers file, clean URLs
(/about serves about.html), 404.html with a 404, and gzip for text. The landing page wakes the API
at /health, which Pages hands to the Worker through apps/web/functions; here a stub answers it the
way the Worker does, so the page logs no error it would not log live. Unlike Pages this server
speaks HTTP/1.1 and gzip rather than HTTP/2 and brotli, so a live run can differ by a point or two;
the file names its target so nobody mistakes one for the other.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import statistics
import subprocess
import tempfile
import threading
import time
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from scripts.harden_lighthouse import LIGHTHOUSE, one_run

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "web"
OUT = ROOT / "results" / "lighthouse_landing.json"
LIVE = "https://second-look-79t.pages.dev/"
CATEGORIES = ("performance", "accessibility", "best-practices", "seo")
TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript",
    ".css": "text/css",
    ".json": "application/json",
    ".txt": "text/plain; charset=utf-8",
    ".jpg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".avif": "image/avif",
    ".woff2": "font/woff2",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".webmanifest": "application/manifest+json",
}
# Pages compresses these on the way out.
TEXT_TYPES = (
    "text/",
    "application/javascript",
    "application/json",
    "image/svg+xml",
    "application/manifest",
)


def header_rules(site: Path) -> list[tuple[str, list[tuple[str, str]]]]:
    """The rules of a Pages _headers file: a path line, then indented header lines."""
    rules: list[tuple[str, list[tuple[str, str]]]] = []
    path = site / "_headers"
    for line in path.read_text(encoding="utf-8").splitlines() if path.exists() else []:
        if not line.strip() or line.startswith("#"):
            continue
        if not line.startswith(" "):
            rules.append((line.strip(), []))
        elif rules:
            name, _, value = line.strip().partition(":")
            rules[-1][1].append((name.strip(), value.strip()))
    return rules


def headers_for(path: str, rules: list[tuple[str, list[tuple[str, str]]]]) -> dict[str, str]:
    out: dict[str, str] = {}
    for pattern, headers in rules:
        exact = pattern == path
        splat = pattern.endswith("/*") and path.startswith(pattern[:-1])
        if exact or splat:
            for name, value in headers:
                out[name] = f"{out[name]}, {value}" if name in out else value
    return out


def file_for(site: Path, path: str) -> Path | None:
    clean = path.split("?", 1)[0].split("#", 1)[0]
    if ".." in clean.split("/"):
        return None
    rel = clean.lstrip("/")
    tries = [site / rel / "index.html"] if clean.endswith("/") else []
    tries += [site / rel, site / f"{rel}.html", site / rel / "index.html"]
    return next((p for p in tries if p.is_file()), None)


class PagesHandler(BaseHTTPRequestHandler):
    """Serves one static export the way Cloudflare Pages does, as far as Lighthouse can tell."""

    def __init__(self, *args: Any, site: Path, rules: list, **kwargs: Any) -> None:
        self.site = site
        self.rules = rules
        super().__init__(*args, **kwargs)

    def log_message(self, format: str, *args: Any) -> None:
        return None

    def send(self, status: int, body: bytes, ctype: str, path: str) -> None:
        headers = {"Content-Type": ctype, "Cache-Control": "public, max-age=0, must-revalidate"}
        headers.update(headers_for(path, self.rules))
        if ctype.startswith(TEXT_TYPES) and "gzip" in self.headers.get("Accept-Encoding", ""):
            body = gzip.compress(body)
            headers["Content-Encoding"] = "gzip"
        self.send_response(status)
        for name, value in headers.items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        # The Worker's answer, which Pages hands on through apps/web/functions.
        if path == "/health":
            self.send(200, b'{"status":"ok"}', "application/json", path)
            return
        if path.startswith("/api/") and not path.startswith("/api/share/"):
            self.send(404, b'{"detail":"not served here"}', "application/json", path)
            return
        found = file_for(self.site, path)
        if found is None:
            missing = self.site / "404.html"
            body = missing.read_bytes() if missing.is_file() else b"not found"
            self.send(404, body, TYPES[".html"], path)
            return
        ctype = TYPES.get(found.suffix, "application/octet-stream")
        self.send(200, found.read_bytes(), ctype, path)

    # Pages answers HEAD like GET without the body, and the app's router sends some.
    do_HEAD = do_GET


def serve(site: Path) -> tuple[ThreadingHTTPServer, str]:
    handler = partial(PagesHandler, site=site, rules=header_rules(site))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}/"


def export_site() -> Path:
    """The static export with the environment scripts/deploy.sh gives it for production."""
    sha = git("rev-parse", "--short", "HEAD")
    env = {
        **os.environ,
        "NEXT_PUBLIC_API_ORIGIN": "",
        "NEXT_PUBLIC_SITE_URL": LIVE.rstrip("/"),
        "NEXT_PUBLIC_BUILD_HASH": sha,
        "NEXT_TELEMETRY_DISABLED": "1",
    }
    # The export rewrites the tracked public/_headers for its API origin; out/ keeps that copy,
    # and the tracked one is put back, so a measurement leaves the tree as it found it.
    tracked = WEB / "public" / "_headers"
    before = tracked.read_bytes()
    try:
        subprocess.run(["npm", "run", "export"], cwd=WEB, env=env, check=True, capture_output=True)
    finally:
        tracked.write_bytes(before)
    return WEB / "out"


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def measure(url: str, runs: int, reports: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    got = [one_run(url, reports / f"landing_{i + 1}.json") for i in range(runs)]
    perf = [r["scores"].get("performance", 0) for r in got]
    return got, got[perf.index(statistics.median_low(perf))]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    where = ap.add_mutually_exclusive_group(required=True)
    where.add_argument("--build", action="store_true", help="export apps/web, then measure it")
    where.add_argument("--dir", type=Path, help="a static export already made")
    where.add_argument("--url", help="a deployed site, such as the live one")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args(argv)

    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    # What differs from the commit named below when the measurement starts, the result aside.
    status = git("status", "--porcelain").splitlines()
    changed = sorted(ln[3:] for ln in status if "lighthouse_landing" not in ln)
    server = None
    if args.url:
        url, target = args.url, "deployed site"
    else:
        site = export_site() if args.build else args.dir.resolve()
        if not (site / "index.html").is_file():
            raise SystemExit(f"no static export in {site}: run with --build")
        server, url = serve(site)
        target = "local static export, served here the way Cloudflare Pages serves it"
    try:
        with tempfile.TemporaryDirectory(prefix="lighthouse-landing-") as tmp:
            runs, median = measure(url, args.runs, Path(tmp))
    finally:
        if server is not None:
            server.shutdown()
    doc = {
        "checked_utc": started,
        "commit": git("rev-parse", "--short", "HEAD"),
        "uncommitted_changes": changed,
        "target": target,
        "url": url if args.url else "/ of the local export",
        "lighthouse": LIGHTHOUSE,
        "profile": "Lighthouse default mobile: simulated throttling, 150 ms RTT, 1.6 Mbps, 4x CPU",
        "cpus": os.cpu_count(),
        "runs": runs,
        "median": median,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    scores = median["scores"]
    print("lighthouse-landing: " + ", ".join(f"{c} {scores.get(c)}" for c in CATEGORIES))
    per_run = [r["scores"].get("performance") for r in runs]
    print(f"lighthouse-landing: performance per run {per_run}")
    low = [c for c in CATEGORIES if (scores.get(c) or 0) < 95]
    return 1 if low else 0


if __name__ == "__main__":
    raise SystemExit(main())
