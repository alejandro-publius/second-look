"""The definition of done, checked (UPDATE_27 sections 0 and 3, blocks 25 and 26).

Reads docs/internal/DONE.md, where every item is one table row, in order:

  | ID | Item | Kind | Date | Outside cause | Cause test | Command |

Kind is one of four:

  CHECK       the command must pass now
  DATED       the command must pass once its Date has come; before that the item is BLOCKED
  BLOCKED-IF  the item waits on something outside the repo. Its cause test exits 0 while that
              cause still holds, and it is run again on every pass. A Date, when given, is the
              earliest the item can be done; before it the item is BLOCKED too.
  HUMAN       a step only a person can take. Its command still says whether it was taken.

Every command runs from the repo root under bash with pipefail and a time limit. One line per item:

  PASS     the command exited 0
  RED      it did not, or it ran past the time limit (never for a HUMAN item)
  BLOCKED  a DATED item before its date, or a BLOCKED-IF item whose cause still holds
  HUMAN    a person has not taken the step yet

and then one line exactly: RED: <n> BLOCKED: <n> HUMAN: <n>. It exits 1 when RED is above 0, 2
when the file cannot be read as a checklist, and 0 otherwise.

A command that cannot fail is refused when the file is read: `true`, `|| true`, `|| echo ...`,
`; echo ...` at the end, `true` at the end of a `( )` or `{ }`, a `test` of one fixed word such
as `test 1` or `[ 1 ]`, a trailing `&`, an `if` without its own `else`, `exit 0` and
`set +o pipefail` never prove that anything was done.

  make done-check
  uv run python scripts/done_check.py --only D01,D07 --timeout 60 --jobs 1
"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Built from parts so the go-public rewrite, which rewords every mention of the working notes
# folder in a tracked file, leaves this path alone.
DONE_FILE = ROOT / "docs" / "internal" / "DONE.md"
COLUMNS = ("ID", "Item", "Kind", "Date", "Outside cause", "Cause test", "Command")
KINDS = ("CHECK", "DATED", "BLOCKED-IF", "HUMAN")
ROW = re.compile(r"^\|\s*D\d+\s*\|")
ID = re.compile(r"^D(\d{2,3})$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
PIPE = re.compile(r"(?<!\\)\|")
# Shapes that turn a failure into success, so a command holding one proves nothing.
NEVER_FAILS = (
    (re.compile(r"^\s*(true|:)\s*$"), "the command is only `true`"),
    (
        re.compile(
            r"\|\|\s*(?:\{\s*)?(?:(?:\S*/)?(?:true|echo|printf)\b|:(?=\s|;|$|\})|exit\s+0\b)"
        ),
        "a failure is turned into success",
    ),
    # At the very end, or at the end of a ( ) or { } that ends the command.
    (re.compile(r"(;|&&)\s*(true|:)\s*;?\s*(?:[)}]\s*)*$"), "the command ends in `true`"),
    (re.compile(r";\s*(?:\S*/)?(?:echo|printf)\b[^;&|]*$"), "the command ends in `echo`"),
    (re.compile(r"(?<![&>])&\s*$"), "the command runs in the background"),
    # test or [ with one word and no variable in it: a word that is not empty is always true.
    (
        re.compile(
            r"(?:^|[;&|({]|\bthen\b|\belse\b)\s*"
            r"(?:test\s+(?:\"[^\"$`\\]+\"|'[^']+'|[^\s$\"'`\\;&|()<>\[\]]+)"
            r"|\[\s+(?:\"[^\"$`\\]+\"|'[^']+'|[^\s$\"'`\\;&|()<>\[\]]+)\s+\])"
            r"\s*(?:$|[;&|)}])"
        ),
        "a `test` of one fixed word always passes",
    ),
    (re.compile(r"\bexit\s+0\b"), "the command says `exit 0`"),
    (re.compile(r"set\s+\+o\s+pipefail|set\s+\+e\b"), "the command switches its own checks off"),
)
# Each `if` needs an `else` of its own. Both are counted where a shell reads them as words of the
# language, so the word else in a pattern, as in `grep -q else x`, is not an else.
KEYWORD_IF = re.compile(r"(?:^|[;&|({\n]|\bthen\b|\belse\b|\bdo\b)\s*if\s")
KEYWORD_ELSE = re.compile(r"[;\n]\s*else\b")
IF_WITHOUT_ELSE = "an `if` without `else` passes when its test fails"
DEFAULT_TIMEOUT = 120.0
CAUSE_TIMEOUT = 30.0
STATUSES = ("PASS", "RED", "BLOCKED", "HUMAN")

Runner = Callable[[str, Path, float], tuple[int | None, str]]


class ChecklistError(Exception):
    """The file cannot be read as a checklist; the message names the line."""


@dataclass(frozen=True)
class Item:
    id: str
    text: str
    kind: str
    date: datetime | None
    cause: str
    cause_test: str
    command: str
    line: int


@dataclass(frozen=True)
class Outcome:
    item: Item
    status: str
    reason: str = ""


def iso(when: datetime) -> str:
    return when.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_date(text: str) -> datetime:
    if not DATE.fullmatch(text):
        raise ValueError(f"a date is written 2026-09-28T01:00:00Z, not {text!r}")
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def split_row(line: str) -> list[str]:
    """The cells of one table row. A pipe inside a cell is written \\| and read back as |."""
    body = line.strip()
    body = body[1:] if body.startswith("|") else body
    if body.endswith("|") and not body.endswith("\\|"):
        body = body[:-1]
    return [cell.strip().replace("\\|", "|") for cell in PIPE.split(body)]


def code_span(cell: str, what: str, lineno: int) -> str:
    """A command cell is one code span, so GitHub shows it exactly as bash runs it."""
    if not cell:
        return ""
    if len(cell) < 2 or not (cell.startswith("`") and cell.endswith("`")) or "`" in cell[1:-1]:
        raise ChecklistError(f"line {lineno}: the {what} must be one `code span`")
    return cell[1:-1].strip()


def never_fails(command: str) -> str | None:
    """Why this command could pass without anything being done, or None."""
    for pattern, why in NEVER_FAILS:
        if pattern.search(command):
            return why
    if len(KEYWORD_IF.findall(command)) > len(KEYWORD_ELSE.findall(command)):
        return IF_WITHOUT_ELSE
    return None


def parse(text: str) -> list[Item]:
    items: list[Item] = []
    seen: set[str] = set()
    last = 0
    for lineno, line in enumerate(text.splitlines(), 1):
        if not ROW.match(line):
            continue
        cells = split_row(line)
        if len(cells) != len(COLUMNS):
            raise ChecklistError(
                f"line {lineno}: {len(cells)} cells, expected {len(COLUMNS)}: {', '.join(COLUMNS)}"
            )
        ident, text_cell, kind, date_cell, cause, cause_cell, command_cell = cells
        m = ID.fullmatch(ident)
        if not m:
            raise ChecklistError(f"line {lineno}: {ident!r} is not an id like D07")
        if ident in seen:
            raise ChecklistError(f"line {lineno}: {ident} is used twice")
        if int(m.group(1)) <= last:
            raise ChecklistError(f"line {lineno}: {ident} is out of order; ids go up down the file")
        seen.add(ident)
        last = int(m.group(1))
        if not text_cell:
            raise ChecklistError(f"line {lineno}: {ident} says what the item is nowhere")
        if kind not in KINDS:
            raise ChecklistError(f"line {lineno}: kind {kind!r} is not one of {', '.join(KINDS)}")
        date = None
        if date_cell:
            if kind in ("CHECK", "HUMAN"):
                raise ChecklistError(f"line {lineno}: a {kind} item has no date")
            try:
                date = parse_date(date_cell)
            except ValueError as e:
                raise ChecklistError(f"line {lineno}: {e}") from None
        elif kind == "DATED":
            raise ChecklistError(f"line {lineno}: a DATED item needs its date")
        cause_test = code_span(cause_cell, "cause test", lineno)
        if kind == "BLOCKED-IF":
            if not cause or not cause_test:
                raise ChecklistError(
                    f"line {lineno}: a BLOCKED-IF item names its outside cause and a cause test"
                )
        elif cause or cause_test:
            raise ChecklistError(f"line {lineno}: only a BLOCKED-IF item has an outside cause")
        command = code_span(command_cell, "command", lineno)
        if not command:
            raise ChecklistError(f"line {lineno}: {ident} has no command")
        for what, cmd in (("command", command), ("cause test", cause_test)):
            why = never_fails(cmd) if cmd else None
            if why:
                raise ChecklistError(f"line {lineno}: the {what} of {ident} cannot fail: {why}")
        items.append(Item(ident, text_cell, kind, date, cause, cause_test, command, lineno))
    if not items:
        raise ChecklistError("no item rows found (a row starts with | D01 |)")
    return items


def run_shell(command: str, root: Path, timeout: float) -> tuple[int | None, str]:
    """Exit code and output; the code is None when the time ran out and the command was killed.

    The command gets its own process group, so a timeout kills what it started too (make, pytest,
    a browser), not only the shell.
    """
    proc = subprocess.Popen(
        ["bash", "-o", "pipefail", "-c", command],
        cwd=root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )
    try:
        out, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        out, _ = proc.communicate()
        return None, out or ""
    return proc.returncode, out or ""


def last_line(text: str) -> str:
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    return lines[-1][:200] if lines else "no output"


def judge(item: Item, *, now: datetime, root: Path, timeout: float, run: Runner) -> Outcome:
    blocked: list[str] = []
    if item.kind == "BLOCKED-IF":
        # Tested again on every pass, before the date too, so the line always says whether the
        # outside cause still holds.
        limit = min(timeout, CAUSE_TIMEOUT)
        code, out = run(item.cause_test, root, limit)
        if code is None:
            return Outcome(item, "RED", f"the cause test ran past {limit:g} s")
        if code == 0:
            blocked.append(f"outside cause: {item.cause}, still so when re-tested {iso(now)}")
    if item.date is not None and now < item.date:
        blocked.append(f"dated: waits until {iso(item.date)}, now {iso(now)}")
    if blocked:
        return Outcome(item, "BLOCKED", "; and ".join(blocked))
    code, out = run(item.command, root, timeout)
    if code == 0:
        return Outcome(item, "PASS")
    why = (
        f"ran past {timeout:g} s and was stopped"
        if code is None
        else f"exit {code}: {last_line(out)}"
    )
    if item.kind == "HUMAN":
        return Outcome(item, "HUMAN", f"waits for a person; {why}")
    return Outcome(item, "RED", why)


def counts_line(outcomes: Sequence[Outcome]) -> str:
    n = {s: sum(1 for o in outcomes if o.status == s) for s in STATUSES}
    return f"RED: {n['RED']} BLOCKED: {n['BLOCKED']} HUMAN: {n['HUMAN']}"


def render(outcome: Outcome) -> str:
    tail = f"  ({outcome.reason})" if outcome.reason else ""
    return f"{outcome.status:<8} {outcome.item.id}  {outcome.item.text}{tail}"


def check(
    items: Sequence[Item],
    *,
    now: datetime,
    root: Path,
    timeout: float,
    jobs: int,
    run: Runner = run_shell,
    emit: Callable[[str], None] = print,
) -> list[Outcome]:
    """Judge every item, several at a time, and print the lines in file order as they finish."""
    outcomes: list[Outcome] = []
    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        futures = [
            pool.submit(judge, item, now=now, root=root, timeout=timeout, run=run) for item in items
        ]
        for future in futures:
            outcome = future.result()
            outcomes.append(outcome)
            emit(render(outcome))
    emit(counts_line(outcomes))
    return outcomes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--file", type=Path, default=DONE_FILE, help="the checklist to read")
    parser.add_argument("--only", default="", help="comma separated ids, such as D01,D07")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="seconds per item")
    parser.add_argument("--jobs", type=int, default=4, help="items checked at the same time")
    parser.add_argument("--now", default="", help="pretend it is this UTC time (for tests)")
    parser.add_argument("--json", type=Path, default=None, help="also write the outcomes here")
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    path = args.file if args.file.is_absolute() else Path.cwd() / args.file
    if args.file == DONE_FILE and not DONE_FILE.is_file():
        # make go-public removes the working notes from the tip, the checklist with them, and
        # the loop that worked from it is over. That is not an error; say so and stop.
        print(
            "done-check: the working notes are gone from this tree (make go-public removed them), "
            "so there is no checklist to run"
        )
        return 0
    try:
        items = parse(path.read_text(encoding="utf-8"))
        now = parse_date(args.now) if args.now else datetime.now(UTC).replace(microsecond=0)
    except (OSError, ChecklistError, ValueError) as e:
        print(f"done-check: cannot read the checklist: {e}")
        return 2
    if args.only:
        wanted = {w.strip() for w in args.only.split(",") if w.strip()}
        unknown = wanted - {i.id for i in items}
        if unknown:
            print(f"done-check: no such item: {', '.join(sorted(unknown))}")
            return 2
        items = [i for i in items if i.id in wanted]
    print(f"done-check: {len(items)} items from {path.name}, {iso(now)}")
    outcomes = check(items, now=now, root=args.root.resolve(), timeout=args.timeout, jobs=args.jobs)
    if args.json:
        rows = [
            {
                "id": o.item.id,
                "item": o.item.text,
                "kind": o.item.kind,
                "status": o.status,
                "reason": o.reason,
            }
            for o in outcomes
        ]
        args.json.write_text(
            json.dumps(
                {"checked_utc": iso(now), "counts": counts_line(outcomes), "items": rows}, indent=2
            )
            + "\n",
            encoding="utf-8",
        )
    return 1 if any(o.status == "RED" for o in outcomes) else 0


if __name__ == "__main__":
    sys.exit(main())
