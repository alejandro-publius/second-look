"""Is the live site up? launchd runs this every 10 minutes through Oct 15 (UPDATE_30 section 7.1).

Each run GETs six addresses on production: /, /judges, /city, one walk, /health and the public
counts. A page must answer 200 with "Second Look" in it; /health must say ok; the counts must be
JSON with by_arm. One failed run is only counted. On the second failed run in a row the outage
begins: a line goes to ~/second-look-backups/uptime.log, one comment to the status issue and one
macOS notification. While it lasts each failed run adds a line to uptime.log and nothing else.
When a run passes again, uptime.log, the status issue and a notification each say how long it was
down, so an outage makes two comments at most, never one every ten minutes.

The brief says /api/health; that address answers 404 on production by design, because the
Worker's health route is /health, which the Pages origin hands to it. So /health is checked.

Each passing run also hands the counts to scripts/panel_status.py, which edits the status
issue's counts paragraph only when a count moved. Everything that leaves this Mac goes through
scripts/outward.py; the test points this at an address that cannot resolve with the network
real and the outputs replaced.

  uv run python scripts/uptime.py
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts import panel_status
from scripts.outward import Outward, Reply

SITE = "https://second-look-79t.pages.dev"
PATHS = ("/", "/judges", "/city", "/walk/v02", "/health", "/api/test/counts")
BACKUPS = Path.home() / "second-look-backups"
OUTAGE_LOG = BACKUPS / "uptime.log"
STATE = BACKUPS / "state" / "uptime.json"
FAILS_TO_ALERT = 2


def stamp(ts: datetime) -> str:
    return ts.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def problem(path: str, reply: Reply) -> str | None:
    """Why this answer is not a working page, or None."""
    if reply.status != 200:
        return f"{path} answered {reply.status or reply.error or 'nothing'}"
    if path == "/health":
        try:
            ok = json.loads(reply.text).get("status") == "ok"
        except (ValueError, AttributeError):
            ok = False
        return None if ok else f"{path} did not say ok"
    if path == "/api/test/counts":
        try:
            ok = "by_arm" in json.loads(reply.text)
        except (ValueError, TypeError):
            ok = False
        return None if ok else f"{path} gave no counts"
    return None if "Second Look" in reply.text else f"{path} is not the Second Look page"


@dataclass
class Outputs:
    """Where an outage is told. The test replaces the log and the state with files in a
    temporary folder, and the outward layer with a stand-in."""

    log: Path = OUTAGE_LOG
    state: Path = STATE
    panel_state: Path = BACKUPS / "state" / "panel_counts.json"


def read_state(path: Path) -> dict[str, Any]:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        return doc if isinstance(doc, dict) else {}
    except (OSError, ValueError):
        return {}


def minutes_between(a: str, b: str) -> int:
    t0 = datetime.fromisoformat(a.replace("Z", "+00:00"))
    t1 = datetime.fromisoformat(b.replace("Z", "+00:00"))
    return round((t1 - t0).total_seconds() / 60)


def run(
    out: Outward,
    *,
    site: str = SITE,
    outputs: Outputs | None = None,
    network: Outward | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    say: Callable[[str], None] = print,
) -> int:
    """One check. `network` does the GETs (the real layer by default, even when `out`, which
    writes the comment and the notification, is a stand-in)."""
    outputs = outputs or Outputs()
    network = network or out
    now = stamp(clock())
    replies = {path: network.get(f"{site}{path}", timeout=20) for path in PATHS}
    problems = [p for p in (problem(path, r) for path, r in replies.items()) if p]
    state = read_state(outputs.state)
    fails = int(state.get("fails", 0))
    down_since = state.get("down_since")

    def outage_line(text: str) -> None:
        outputs.log.parent.mkdir(parents=True, exist_ok=True)
        with outputs.log.open("a", encoding="utf-8") as f:
            f.write(f"{now} {text}\n")

    if problems:
        fails += 1
        what = "; ".join(problems)
        if fails >= FAILS_TO_ALERT and not down_since:
            down_since = now
            outage_line(f"DOWN: {fails} failed checks in a row at {site}: {what}")
            out.comment(
                f"Uptime ({now}): {site} failed {fails} checks in a row, ten minutes apart: "
                f"{what}. If it stays down, `make rollback` shows the way back "
                "(~/second-look-backups/uptime.log)."
            )
            out.notify("Second Look is down", what[:180])
        elif down_since:
            outage_line(f"still down since {down_since}: {what}")
        say(f"{now} uptime: FAILED ({fails} in a row): {what}")
    else:
        if down_since:
            minutes = minutes_between(down_since, now)
            outage_line(f"UP again at {site}, after about {minutes} minutes down")
            out.comment(f"Uptime ({now}): {site} answers again, after about {minutes} minutes.")
            out.notify("Second Look is back up", f"after about {minutes} minutes")
        fails, down_since = 0, None
        say(f"{now} uptime: all {len(PATHS)} addresses answered at {site}")
        counts = replies["/api/test/counts"]
        try:
            doc = json.loads(counts.text)
            say(panel_status.update_issue(out, doc, when=now, state=outputs.panel_state))
        except ValueError:
            pass
    outputs.state.parent.mkdir(parents=True, exist_ok=True)
    outputs.state.write_text(
        json.dumps({"fails": fails, "down_since": down_since, "checked": now}) + "\n",
        encoding="utf-8",
    )
    return 1 if problems else 0


def main() -> int:
    return run(Outward())


if __name__ == "__main__":
    sys.exit(main())
