"""make rollback: put the last known good Worker version and Pages build back on production.

The deploy record in docs/notes/hosting.md (scripts/deploy_record.py) lists every production
deploy, newest first, and marks a row good once the phone tests passed against it. For each part
this picks the newest good row that is not what is live now, and:

- the Worker: `wrangler rollback <version id>`, which makes that version live again;
- the site: uploads the kept files of that build again (Pages has no rollback on the command
  line), with the build's commit as the deployment's commit, so the record still matches it.

Without --yes it only prints what it would do, and changes nothing. D1 tables are never rolled
back: every schema change is additive. All it does outside this machine goes through
scripts/outward.py, so the tests replace it.

  make rollback                   what would happen
  make rollback ROLLBACK=yes      do it
  uv run python scripts/rollback.py --only web --yes
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from scripts import deploy_record as dr
from scripts.outward import Outward

ROOT = Path(__file__).resolve().parents[1]
SITE = "https://second-look-79t.pages.dev"


@dataclass
class Step:
    part: str
    row: dr.Row
    argv: list[str]
    cwd: Path

    def describe(self) -> str:
        where = dr.home_path(self.cwd)
        return (
            f"{self.part}: back to {self.row.id} from commit {self.row.commit}: "
            f"in {where}, run {' '.join(self.argv)}"
        )


@dataclass
class Plan:
    steps: list[Step] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def worker_step(row: dr.Row, root: Path) -> Step:
    argv = [
        "npx", "wrangler", "rollback", row.id, "--name", dr.WORKER_NAME,
        "--message", f"rollback to {row.commit}", "--yes",
    ]  # fmt: skip
    return Step("worker", row, argv, root / "worker")


def web_step(row: dr.Row) -> Step:
    argv = [
        "npx", "wrangler", "pages", "deploy", "out", "--project-name", dr.PAGES_PROJECT,
        "--branch", "main", "--commit-hash", row.commit,
        "--commit-message", f"rollback to {row.commit}", "--commit-dirty=true",
    ]  # fmt: skip
    return Step("web", row, argv, dr.expand(row.archive))


def choose(rows: list[dr.Row], part: str, live: str | None) -> tuple[dr.Row | None, str]:
    """The newest good row of a part that differs from what is live (or, when that cannot be
    read, from the newest row), with a sentence saying why."""
    mine = [r for r in rows if r.part == part]
    if not mine:
        return None, f"{part}: the deploy record has no row yet"

    def key(r: dr.Row) -> str:
        return r.id if part == "worker" else r.commit[:7]

    current = live if live is not None else key(mine[0])
    for r in mine:
        if not r.checked or key(r) == current:
            continue
        if part == "web" and not dr.expand(r.archive).is_dir():
            continue
        return r, ""
    return (
        None,
        f"{part}: no good row other than what is live ({current}), so nothing to go back to",
    )


def plan(
    rows: list[dr.Row],
    live_worker: str | None,
    live_pages: dict[str, str] | None,
    *,
    root: Path = ROOT,
    only: str | None = None,
) -> Plan:
    out = Plan()
    if live_worker is None:
        out.notes.append("the live Worker version could not be read; compared with the newest row")
    if live_pages is None:
        out.notes.append("the live Pages build could not be read; compared with the newest row")
    for part in ("worker", "web") if only is None else (only,):
        live = live_worker if part == "worker" else (live_pages or {}).get("commit", "")[:7] or None
        row, why = choose(rows, part, live)
        if row is None:
            out.notes.append(why)
        elif part == "worker":
            out.steps.append(worker_step(row, root))
        else:
            out.steps.append(web_step(row))
    return out


def to_targets(worker_row: dr.Row | None, web_row: dr.Row | None, root: Path = ROOT) -> Plan:
    """A plan back to two known rows, for a job that recorded them before it deployed."""
    out = Plan()
    if worker_row is not None:
        out.steps.append(worker_step(worker_row, root))
    if web_row is not None:
        out.steps.append(web_step(web_row))
    return out


def carry_out(the_plan: Plan, out: Outward, say: Callable[[str], None] = print) -> bool:
    """Run each step; True when every one worked. The site is checked afterwards."""
    ok = True
    for step in the_plan.steps:
        done = out.run(step.argv, cwd=step.cwd, timeout=1800)
        line = f"rollback: {step.part} back to {step.row.id} ({step.row.commit}): "
        line += "done" if done.ok else f"FAILED: {done.tail()}"
        say(line)
        ok = ok and done.ok
    if the_plan.steps:
        health = out.get(f"{SITE}/health")
        say(f"rollback: {SITE}/health answered {health.status or health.error}")
        ok = ok and health.status == 200
    return ok


def main(argv: list[str] | None = None, out: Outward | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--yes", action="store_true", help="really do it; without it, dry run")
    parser.add_argument("--only", choices=dr.PARTS, default=None)
    args = parser.parse_args(argv)
    out = out or Outward()
    rows = dr.load()
    the_plan = plan(rows, dr.live_worker(out), dr.live_pages(out), only=args.only)
    for note in the_plan.notes:
        print(f"rollback: {note}")
    if not the_plan.steps:
        print("rollback: nothing to do")
        return 1
    for step in the_plan.steps:
        print(f"rollback: {'will' if args.yes else 'would'} {step.describe()}")
    if not args.yes:
        print("rollback: dry run, nothing changed. Run make rollback ROLLBACK=yes to do it.")
        return 0
    ok = carry_out(the_plan, out)
    print(
        "rollback: finished. Run the phone tests against production (docs/notes/hosting.md, "
        "steps 3 and 5)."
        if ok
        else "rollback: a step FAILED; production may be half way. Read the lines above."
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
