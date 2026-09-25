"""Watch hl7-eu/oah for replies to what we sent them, once a day (UPDATE_30 section 6.2).

Reads pull request 5 and issues 6, 7 and 8 with `gh pr view` and `gh issue view`, the pull
request's reviews included. A comment or review from someone the repository lists as an owner,
member or collaborator that was not there on an earlier run is written to
~/second-look-backups/logs/hl7.log and to the status issue, with its link. Other new comments go
to the log only. It only reads: it never replies, reacts or pushes anything to hl7-eu. A change a
maintainer asks for is made by a person on the fork branch.

What was already seen is kept in ~/second-look-backups/state/hl7_seen.json. Everything that
leaves this Mac goes through scripts/outward.py, so the tests replace it.

  uv run python scripts/hl7_watch.py
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.outward import Outward

REPO = "hl7-eu/oah"
WATCHED = (("pr", 5), ("issue", 6), ("issue", 7), ("issue", 8))
MAINTAINERS = {"OWNER", "MEMBER", "COLLABORATOR"}
BACKUPS = Path.home() / "second-look-backups"
LOG = BACKUPS / "logs" / "hl7.log"
STATE = BACKUPS / "state" / "hl7_seen.json"


def stamp(ts: datetime) -> str:
    return ts.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def view(out: Outward, kind: str, number: int) -> dict[str, Any] | None:
    fields = "state,url,comments" + (",reviews" if kind == "pr" else "")
    done = out.run(["gh", kind, "view", str(number), "--repo", REPO, "--json", fields], timeout=120)
    if not done.ok:
        return None
    try:
        doc = json.loads(done.out)
    except ValueError:
        return None
    return doc if isinstance(doc, dict) else None


def notes(doc: dict[str, Any]) -> list[dict[str, str]]:
    """Every comment and review with a body, as id, author, role, time, link and text."""
    found = []
    for c in doc.get("comments") or []:
        found.append(
            {
                "id": str(c.get("id") or c.get("url") or ""),
                "author": str((c.get("author") or {}).get("login", "")),
                "role": str(c.get("authorAssociation", "")),
                "at": str(c.get("createdAt", "")),
                "url": str(c.get("url") or doc.get("url", "")),
                "body": str(c.get("body") or ""),
            }
        )
    for r in doc.get("reviews") or []:
        if not (r.get("body") or r.get("state") in ("CHANGES_REQUESTED", "APPROVED")):
            continue
        found.append(
            {
                "id": str(r.get("id") or ""),
                "author": str((r.get("author") or {}).get("login", "")),
                "role": str(r.get("authorAssociation", "")),
                "at": str(r.get("submittedAt", "")),
                "url": str(doc.get("url", "")),
                "body": f"[review: {r.get('state', '')}] {r.get('body') or ''}".strip(),
            }
        )
    return [n for n in found if n["id"]]


def short(text: str, n: int = 300) -> str:
    one = " ".join(text.split())
    return one if len(one) <= n else one[: n - 3].rsplit(" ", 1)[0] + "..."


def run(
    out: Outward,
    *,
    log: Path = LOG,
    state_path: Path = STATE,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    say: Callable[[str], None] = print,
) -> int:
    now = stamp(clock())
    try:
        seen: dict[str, Any] = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        seen = {}
    ids = set(seen.get("ids", []))
    states: dict[str, str] = dict(seen.get("states", {}))
    lines: list[str] = []
    posts: list[str] = []
    unread = 0
    for kind, number in WATCHED:
        name = f"{'pull request' if kind == 'pr' else 'issue'} {number}"
        doc = view(out, kind, number)
        if doc is None:
            unread += 1
            lines.append(f"{now} hl7: could not read {REPO} {name} with gh")
            continue
        state = str(doc.get("state", ""))
        key = f"{kind}{number}"
        if key in states and states[key] != state:
            lines.append(f"{now} hl7: {REPO} {name} is now {state}: {doc.get('url', '')}")
            posts.append(f"hl7-eu/oah {name} is now {state}: {doc.get('url', '')}")
        states[key] = state
        for note in notes(doc):
            if note["id"] in ids:
                continue
            ids.add(note["id"])
            maintainer = note["role"] in MAINTAINERS
            who = f"{note['author']} ({note['role'].lower() or 'no role'})"
            lines.append(
                f"{now} hl7: new {'maintainer ' if maintainer else ''}comment on {name} by {who} "
                f"at {note['at']}: {note['url']}\n    {short(note['body'], 2000)}"
            )
            if maintainer:
                posts.append(
                    f"A maintainer of hl7-eu/oah, {note['author']}, wrote on {name} at "
                    f'{note["at"]}: "{short(note["body"])}" {note["url"]} . Nothing was sent '
                    "back; any change they ask for goes on the fork branch by hand."
                )
    if not lines:
        lines.append(f"{now} hl7: read {REPO} pull request 5 and issues 6, 7 and 8; nothing new")
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    for line in lines:
        say(line)
    for post in posts:
        out.comment(f"hl7 watch ({now}): {post}")
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps({"ids": sorted(ids), "states": states}, indent=1) + "\n", encoding="utf-8"
    )
    return 1 if unread == len(WATCHED) else 0


def main() -> int:
    return run(Outward())


if __name__ == "__main__":
    sys.exit(main())
