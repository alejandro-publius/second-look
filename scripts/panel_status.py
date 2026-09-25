"""How the panel study is doing: completed sessions by source and by arm, from the live counts.

Reads only the public counts endpoint, the same one the site shows; test sessions are never in it.

  uv run python scripts/panel_status.py            the live site
  uv run python scripts/panel_status.py --issue    also put the counts on the status issue
  SITE_URL=http://localhost:3100 uv run python scripts/panel_status.py

With --issue the counts go into a marked paragraph of the status issue's body, right under its
top paragraph, which stays Alex's list. The body is edited only when a count has changed since
the last edit, so the uptime job can call this every ten minutes and the lock job once at the
end. Everything that leaves this Mac goes through scripts/outward.py.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.outward import Outward

SITE = "https://second-look-79t.pages.dev"
TARGET = 80
# The plan's one confirmatory test needs this many completed sessions in each arm (item 7).
MIN_PER_ARM = 20
ARMS = ("trained", "untrained")
START = "<!-- panel-counts -->"
END = "<!-- /panel-counts -->"
STATE = Path.home() / "second-look-backups" / "state" / "panel_counts.json"


def completed(counts: dict[str, Any], arm: str) -> int:
    return int(((counts.get("by_arm") or {}).get(arm) or {}).get("completed", 0))


def render(counts: dict[str, Any]) -> str:
    by_source = counts.get("by_source") or {}
    by_arm = counts.get("by_arm") or {}
    lines = ["Completed sessions by source:"]
    lines += [f"  {name:<12} {n}" for name, n in sorted(by_source.items())]
    lines.append("By arm (randomized, completed):")
    lines += [
        f"  {arm:<12} {v.get('randomized', 0)}, {v.get('completed', 0)}"
        for arm, v in sorted(by_arm.items())
    ]
    panel = int(by_source.get("panel", 0))
    lines.append(f"Panel: {panel} of the {TARGET} completed sessions the study asks for.")
    lines.append(threshold_line(counts))
    return "\n".join(lines)


def threshold_line(counts: dict[str, Any]) -> str:
    fewest = min(completed(counts, arm) for arm in ARMS)
    if fewest >= MIN_PER_ARM:
        return (
            f"Each arm has {MIN_PER_ARM} or more completed sessions, "
            "so the plan's one test applies."
        )
    return (
        f"The plan's one test needs {MIN_PER_ARM} completed sessions in each arm; with fewer the "
        "result is a description."
    )


def issue_block(counts: dict[str, Any], when: str) -> str:
    """The paragraph on the status issue: the counts by arm and by source, and the time."""
    by_source = {k: int(v) for k, v in (counts.get("by_source") or {}).items() if int(v)}
    sources = ", ".join(f"{k} {v}" for k, v in sorted(by_source.items())) or "none yet"
    arms = ", ".join(f"{arm} {completed(counts, arm)}" for arm in ARMS)
    return (
        f"{START}\n**Panel study, {when}:** completed sessions by arm: {arms}; by source: "
        f"{sources}. {threshold_line(counts)} (`make panel-status`)\n{END}"
    )


def put_block(body: str, block: str) -> str:
    """The body with the block in place: where it was, or else right under the top paragraph."""
    a, b = body.find(START), body.find(END)
    if a >= 0 and b > a:
        return body[:a] + block + body[b + len(END) :]
    parts = body.split("\n\n", 1)
    if len(parts) == 1:
        return body.rstrip("\n") + "\n\n" + block + "\n"
    return parts[0] + "\n\n" + block + "\n\n" + parts[1]


def key(counts: dict[str, Any]) -> str:
    """What must change for the issue to be edited again: the arms and the sources, not the time."""
    return json.dumps(
        {"by_arm": counts.get("by_arm"), "by_source": counts.get("by_source")}, sort_keys=True
    )


def update_issue(
    out: Outward,
    counts: dict[str, Any],
    *,
    when: str,
    state: Path | None = None,
    force: bool = False,
) -> str:
    """Edit the status issue's counts paragraph if the counts moved; say what happened."""
    state = state or STATE
    seen = ""
    try:
        seen = state.read_text(encoding="utf-8")
    except OSError:
        pass
    if not force and seen == key(counts):
        return "panel-status: counts unchanged, the status issue was left alone"
    body = out.issue_body()
    if body is None:
        return "panel-status: could not read the status issue"
    done = out.set_issue_body(put_block(body, issue_block(counts, when)))
    if not done.ok:
        return f"panel-status: could not edit the status issue: {done.tail()}"
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text(key(counts), encoding="utf-8")
    return "panel-status: the status issue shows the new counts"


def read_counts(out: Outward, site: str) -> dict[str, Any] | None:
    reply = out.get(f"{site}/api/test/counts")
    if reply.status != 200:
        return None
    try:
        doc = reply.json()
    except ValueError:
        return None
    return doc if isinstance(doc, dict) and "by_arm" in doc else None


def main(argv: list[str] | None = None, out: Outward | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--issue", action="store_true", help="also update the status issue")
    args = parser.parse_args(argv)
    out = out or Outward()
    site = os.environ.get("SITE_URL", SITE).rstrip("/")
    counts = read_counts(out, site)
    if counts is None:
        print(f"panel-status: could not read {site}/api/test/counts")
        return 1
    print(render(counts))
    if args.issue:
        when = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
        print(update_issue(out, counts, when=when))
    return 0


if __name__ == "__main__":
    sys.exit(main())
