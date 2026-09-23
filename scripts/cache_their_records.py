"""Fetch the lab record /two shows from their sandbox, on the Mac, and store it in D1.

On 2026-09-23 the Worker's own fetch got Cloudflare's origin DNS error (HTTP 530, code 1016):
the sandbox's name had dropped out of their DNS. So the Worker never fetches it (see
worker/src/two.ts): this script does, from the Mac, once a day through launchd
(scripts/install_cache_job.sh), and the Worker shows what it stored with the time it was fetched.
While their name does not resolve, the fetch fails, nothing is stored and the page says so.

One read-only GET to their sandbox per run, with the same query, user agent and one second pacing
as apps/api/fhir_routes.py (hard rule 10). Their record goes into the sandbox_cache table only,
never into git. A failed fetch stores nothing, so the last good copy stays.

  uv run python scripts/cache_their_records.py            fetch, store, then read /api/two back
  uv run python scripts/cache_their_records.py --dry-run  fetch and print the SQL, store nothing
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from apps.api import fhir_routes  # noqa: E402

SITE = "https://second-look-79t.pages.dev"
DATABASE = "second-look"


def cache_key(query: dict[str, str]) -> str:
    """The key the Worker reads: sha256 over JSON.stringify(query), first 16 hex digits."""
    text = json.dumps(query, separators=(",", ":"), ensure_ascii=False)
    return "theirs-" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def sql_literal(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def insert_sql(key: str, observation: dict[str, Any], fetched_at: str) -> str:
    body = json.dumps(observation, separators=(",", ":"), ensure_ascii=False)
    return (
        "INSERT OR REPLACE INTO sandbox_cache (cache_key, body, status, fetched_at) VALUES "
        f"({sql_literal(key)}, {sql_literal(body)}, 'ok', {sql_literal(fetched_at)});\n"
    )


def store(sql: str) -> None:
    """Run the one statement against the live D1 database with the wrangler login on this Mac."""
    with tempfile.NamedTemporaryFile("w", suffix=".sql", delete=False, encoding="utf-8") as f:
        f.write(sql)
        path = f.name
    try:
        subprocess.run(
            ["npx", "--yes", "wrangler", "d1", "execute", DATABASE, "--remote", "--file", path],
            cwd=ROOT / "worker",
            check=True,
            capture_output=True,
            text=True,
        )
    finally:
        os.unlink(path)


def read_back(site: str) -> dict[str, Any]:
    response = httpx.get(f"{site.rstrip('/')}/api/two", timeout=20)
    response.raise_for_status()
    return dict(response.json())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="fetch and print, store nothing")
    parser.add_argument("--site", default=SITE, help="where to read /api/two back")
    args = parser.parse_args(argv)

    if "api.enora-oah.eu" in fhir_routes.sandbox_base_url():
        print("cache-theirs: refusing api.enora-oah.eu (hard rule 9)")
        return 2
    observation = fhir_routes.fetch_theirs_live()
    if observation is None:
        print("cache-theirs: their sandbox gave no Observation; the last stored copy stays")
        return 1
    fetched_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    key = cache_key(fhir_routes.theirs_query())
    sql = insert_sql(key, observation, fetched_at)
    if args.dry_run:
        print(sql, end="")
        return 0
    store(sql)
    pair = read_back(args.site)
    theirs = pair.get("theirs") or {}
    if pair.get("theirs_status") != "cached" or theirs.get("id") != observation.get("id"):
        print(f"cache-theirs: stored under {key}, but /api/two says {pair.get('theirs_status')}")
        return 1
    print(
        f"cache-theirs: Observation/{observation.get('id')} fetched at {fetched_at}, stored under "
        f"{key}, and /api/two shows it"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
