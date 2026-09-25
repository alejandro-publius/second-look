"""The daily re-push to their sandbox, retried until its name resolves again (UPDATE_30 6.1).

Their sandbox's name dropped out of DNS on 2026-09-23 (docs/notes/hosting.md). launchd runs this
every day at 08:00 (scripts/mac_jobs.py, the job `repush`). While the name does not resolve it
sends nothing and says so in the log. When it resolves, it:

1. puts our Library entry and the golden visit back by conditional create
   (scripts/repush_sandbox.py --bundle fhir/golden/visit-strawberry-creek-1.json --library),
   which is a no-op for whatever is still there (hard rule 10);
2. updates the cached record behind /two (scripts/cache_their_records.py);
3. writes a line to the status issue, once when it comes back, not every day after.

A failed push while the name resolves is written to the status issue once as well. The state
between runs is in ~/second-look-backups/state/sandbox.json. Everything that leaves this Mac,
the name lookup included, goes through scripts/outward.py, so the tests replace it.

  uv run python scripts/sandbox_retry.py
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

from scripts import repush_sandbox
from scripts.outward import Outward

ROOT = Path(__file__).resolve().parents[1]
STATE = Path.home() / "second-look-backups" / "state" / "sandbox.json"
GOLDEN = "fhir/golden/visit-strawberry-creek-1.json"
FORBIDDEN = "api.enora-oah.eu"


def stamp(ts: datetime) -> str:
    return ts.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_state(path: Path) -> dict[str, str]:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        return doc if isinstance(doc, dict) else {}
    except (OSError, ValueError):
        return {}


def write_state(path: Path, state: str, since: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"state": state, "since": since}) + "\n", encoding="utf-8")


def run(
    out: Outward,
    *,
    base: str = repush_sandbox.DEFAULT_BASE,
    root: Path = ROOT,
    state_path: Path = STATE,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    say: Callable[[str], None] = print,
) -> int:
    now = stamp(clock())
    if FORBIDDEN in base:
        say(f"{now} repush: refusing {FORBIDDEN} (hard rule 9)")
        return 2
    host = urlparse(base).hostname or base
    before = read_state(state_path)
    since = before.get("since", now)
    if not out.resolves(host):
        write_state(state_path, "down", since if before.get("state") == "down" else now)
        say(f"{now} repush: {host} still does not resolve, so nothing was sent; again tomorrow")
        return 0
    env = {"SANDBOX_MIRROR_ENABLED": "true", "SANDBOX_BASE_URL": base}
    pushed = out.run(
        ["uv", "run", "python", "scripts/repush_sandbox.py", "--bundle", GOLDEN, "--library"],
        cwd=root,
        env=env,
    )
    cached = out.run(["uv", "run", "python", "scripts/cache_their_records.py"], cwd=root, env=env)
    if pushed.ok and cached.ok:
        say(f"{now} repush: {host} resolves; Library entry and golden visit put back, /two updated")
        if before.get("state") != "up":
            out.comment(
                f"Their sandbox answers again ({now}): {host} resolves, so the daily job put our "
                "Library entry and the golden visit back by conditional create, and the cached "
                "record behind /two is updated."
            )
        write_state(state_path, "up", since if before.get("state") == "up" else now)
        return 0
    failed = pushed if not pushed.ok else cached
    what = "the re-push" if not pushed.ok else "the /two cache"
    say(f"{now} repush: {host} resolves, but {what} failed: {failed.tail()}")
    if before.get("state") != "failed":
        out.comment(
            f"Their sandbox's name resolves again ({now}), but {what} failed: {failed.tail()}. "
            "The daily job tries again tomorrow at 08:00 (~/second-look-backups/logs/repush.log)."
        )
    write_state(state_path, "failed", since if before.get("state") == "failed" else now)
    return 1


def main() -> int:
    return run(Outward())


if __name__ == "__main__":
    sys.exit(main())
