"""done-check: the checklist is read strictly, every kind prints the right word, the counts line is
exact, a timeout is RED, a dated item waits for its date, and the exit code follows RED only."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

import pytest

from scripts import done_check as dc
from scripts import done_items

ROOT = Path(__file__).resolve().parents[2]
HEADER = (
    "| ID | Item | Kind | Date | Outside cause | Cause test | Command |\n"
    "|---|---|---|---|---|---|---|\n"
)
BEFORE = datetime(2026, 9, 24, 6, 0, tzinfo=UTC)
AFTER = datetime(2026, 9, 29, 0, 0, tzinfo=UTC)


def table(*rows: str) -> str:
    return "# Done\n\n" + HEADER + "\n".join(rows) + "\n"


def row(
    ident: str,
    command: str,
    kind: str = "CHECK",
    date: str = "",
    cause: str = "",
    cause_test: str = "",
    text: str = "",
) -> str:
    command = command.replace("|", "\\|")
    cause_test = cause_test.replace("|", "\\|")
    ct = f"`{cause_test}`" if cause_test else ""
    return (
        f"| {ident} | {text or 'item ' + ident} | {kind} | {date} | {cause} | {ct} | `{command}` |"
    )


def run_main(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], text: str, *extra: str
) -> tuple[int, list[str]]:
    done = tmp_path / "DONE.md"
    done.write_text(text, encoding="utf-8")
    code = dc.main(["--file", str(done), "--root", str(tmp_path), "--jobs", "2", *extra])
    return code, capsys.readouterr().out.splitlines()


# Parsing


def test_a_row_is_read_with_its_escaped_pipes_given_back() -> None:
    items = dc.parse(table(row("D01", "grep -c x file | grep -qx 1")))
    assert len(items) == 1
    assert items[0].command == "grep -c x file | grep -qx 1"
    assert items[0].kind == "CHECK" and items[0].date is None


def test_rows_outside_tables_and_prose_are_ignored() -> None:
    text = "Some words about D01.\n\n" + table(row("D01", "test -f a"), row("D02", "test -f b"))
    assert [i.id for i in dc.parse(text)] == ["D01", "D02"]


def test_a_dated_row_keeps_its_date() -> None:
    items = dc.parse(table(row("D01", "test -f a", "DATED", "2026-09-28T01:00:00Z")))
    assert items[0].date == datetime(2026, 9, 28, 1, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("bad", "message"),
    [
        (row("D01", "test -f a", "MAYBE"), "is not one of"),
        (row("D01", "test -f a", "DATED"), "needs its date"),
        (row("D01", "test -f a", "DATED", "Sep 28"), "a date is written"),
        (row("D01", "test -f a", "CHECK", "2026-09-28T01:00:00Z"), "has no date"),
        (row("D01", "test -f a", "HUMAN", "2026-09-28T01:00:00Z"), "has no date"),
        (row("D01", "test -f a", "BLOCKED-IF"), "names its outside cause"),
        (row("D01", "test -f a", "BLOCKED-IF", cause="DNS down"), "names its outside cause"),
        (row("D01", "test -f a", cause="DNS down"), "only a BLOCKED-IF"),
        ("| D01 | item | CHECK | | | | test -f a |", "one `code span`"),
        ("| D01 | item | CHECK | | | | `test -f a` | extra |", "cells, expected 7"),
        ("| D1 | item | CHECK | | | | `test -f a` |", "not an id"),
        ("| D01 |  | CHECK | | | | `test -f a` |", "says what the item is nowhere"),
        ("| D01 | item | CHECK | | | | `` |", "has no command"),
    ],
)
def test_a_malformed_row_is_refused_with_its_line(bad: str, message: str) -> None:
    with pytest.raises(dc.ChecklistError, match=re.escape(message)) as err:
        dc.parse(table(bad))
    assert "line 5" in str(err.value)


def test_ids_must_be_unique_and_go_up() -> None:
    with pytest.raises(dc.ChecklistError, match="used twice"):
        dc.parse(table(row("D01", "test -f a"), row("D01", "test -f b")))
    with pytest.raises(dc.ChecklistError, match="out of order"):
        dc.parse(table(row("D02", "test -f a"), row("D01", "test -f b")))


def test_a_file_without_rows_is_refused() -> None:
    with pytest.raises(dc.ChecklistError, match="no item rows"):
        dc.parse("# Done\n\nNothing yet.\n")


@pytest.mark.parametrize(
    "command",
    [
        "true",
        ":",
        "test -f a || true",
        "test -f a || :",
        "test -f a || echo missing",
        "test -f a || printf no",
        "test -f a || exit 0",
        "test -f a; true",
        "test -f a && true",
        "test -f a; exit 0",
        "set +o pipefail; false | cat",
        "set +e; false",
        "test -f a; echo checked",
        "test -f a;echo",
        "test -f a; printf ok",
        "test -f a; /bin/echo done",
        "test -f a || /usr/bin/true",
        "test -f a || { :; }",
        "test -f a || { true; }",
        "test -f a &",
        "if test -f a; then echo y; fi",
        "x=1; if test -f a; then echo y; fi",
        # REVIEW_03 R53: five shapes that passed the guard and pass with the file missing.
        "test -f missing || test 1",
        "test -f missing || [ 1 ]",
        "test -f missing; test 1",
        "(test -f missing; true)",
        "grep -q else x; if test -f missing; then false; fi",
        # and their near kin
        "test -f a || test 'yes'",
        'test -f a || [ "ok" ]',
        "{ test -f a; true; }",
        "(test -f a && :)",
        "if a; then b; else c; fi; if test -f a; then false; fi",
        "if test -f a; then false; elif test -f b; then false; fi",
    ],
)
def test_a_command_that_cannot_fail_is_refused(command: str) -> None:
    with pytest.raises(dc.ChecklistError, match="cannot fail"):
        dc.parse(table(row("D01", command)))


def test_a_cause_test_that_cannot_fail_is_refused() -> None:
    bad = row("D01", "test -f a", "BLOCKED-IF", cause="their DNS", cause_test="true")
    with pytest.raises(dc.ChecklistError, match="cause test of D01 cannot fail"):
        dc.parse(table(bad))


@pytest.mark.parametrize(
    "command",
    [
        "test -f a",
        "! test -f a",
        "grep -q x a || grep -q y a",
        "make readability",
        "[ 1 -le 12 ]",
        "test -f a && echo ok",
        "grep -q x a &>/dev/null",
        'grep -q "if " a',
        "if test -f a; then test -s a; else false; fi",
        'n=$(wc -l < a) && [ "$n" -ge 8 ]',
        'test -n "$x"',
        '[ "$x" ]',
        "(test -f a; test -f b)",
        "(test -f a; true) && test -f b",
        "grep -q else a",
        # R53's sixth shape: `! true` never passes, so this is `! test -f missing`, which fails
        # once the file exists, like `! test -f a` above.
        "! test -f missing || ! true",
    ],
)
def test_ordinary_commands_are_accepted(command: str) -> None:
    assert dc.parse(table(row("D01", command)))[0].command == command


# Judging one item


def fake(results: Mapping[str, tuple[int | None, str]]) -> dc.Runner:
    def run(command: str, root: Path, timeout: float) -> tuple[int | None, str]:
        return results[command]

    return run


def item(kind: str = "CHECK", date: datetime | None = None, cause_test: str = "") -> dc.Item:
    cause = "their sandbox name does not resolve" if kind == "BLOCKED-IF" else ""
    return dc.Item("D01", "the item", kind, date, cause, cause_test, "cmd", 1)


def judge(it: dc.Item, results: Mapping[str, tuple[int | None, str]], now: datetime) -> dc.Outcome:
    return dc.judge(it, now=now, root=ROOT, timeout=5, run=fake(results))


def test_a_check_passes_or_goes_red_on_its_exit_code() -> None:
    assert judge(item(), {"cmd": (0, "")}, BEFORE).status == "PASS"
    red = judge(item(), {"cmd": (1, "first\nthe last line\n")}, BEFORE)
    assert red.status == "RED" and red.reason == "exit 1: the last line"


def test_a_timeout_is_red() -> None:
    out = judge(item(), {"cmd": (None, "")}, BEFORE)
    assert out.status == "RED" and "ran past 5 s" in out.reason


def test_a_dated_item_is_blocked_before_its_date_and_never_runs() -> None:
    lock = datetime(2026, 9, 28, 1, 0, tzinfo=UTC)
    out = judge(item("DATED", lock), {}, BEFORE)  # an empty runner raises if anything runs
    assert out.status == "BLOCKED"
    assert "2026-09-28T01:00:00Z" in out.reason and "2026-09-24T06:00:00Z" in out.reason


def test_a_dated_item_runs_once_its_date_has_come() -> None:
    lock = datetime(2026, 9, 28, 1, 0, tzinfo=UTC)
    assert judge(item("DATED", lock), {"cmd": (1, "no")}, AFTER).status == "RED"
    assert judge(item("DATED", lock), {"cmd": (0, "")}, AFTER).status == "PASS"
    assert judge(item("DATED", lock), {"cmd": (0, "")}, lock).status == "PASS"


def test_a_blocked_if_item_is_blocked_while_its_cause_holds() -> None:
    out = judge(item("BLOCKED-IF", cause_test="cause"), {"cause": (0, "")}, AFTER)
    assert out.status == "BLOCKED"
    assert "their sandbox name does not resolve" in out.reason
    assert "2026-09-29T00:00:00Z" in out.reason


def test_a_blocked_if_item_runs_its_command_once_the_cause_clears() -> None:
    cleared: dict[str, tuple[int | None, str]] = {"cause": (1, ""), "cmd": (1, "no push")}
    assert judge(item("BLOCKED-IF", cause_test="cause"), cleared, AFTER).status == "RED"
    cleared["cmd"] = (0, "")
    assert judge(item("BLOCKED-IF", cause_test="cause"), cleared, AFTER).status == "PASS"


def test_a_blocked_if_cause_is_tested_before_its_date_too() -> None:
    lock = datetime(2026, 9, 28, 1, 0, tzinfo=UTC)
    held = judge(item("BLOCKED-IF", lock, "cause"), {"cause": (0, "")}, BEFORE)
    assert held.status == "BLOCKED" and "outside cause" in held.reason and "dated" in held.reason
    cleared = judge(item("BLOCKED-IF", lock, "cause"), {"cause": (1, "")}, BEFORE)
    assert cleared.status == "BLOCKED" and "outside cause" not in cleared.reason


def test_a_cause_test_that_hangs_is_red_not_blocked() -> None:
    out = judge(item("BLOCKED-IF", cause_test="cause"), {"cause": (None, "")}, AFTER)
    assert out.status == "RED"


def test_a_human_item_is_human_until_done_and_never_red() -> None:
    assert judge(item("HUMAN"), {"cmd": (1, "not yet")}, BEFORE).status == "HUMAN"
    assert judge(item("HUMAN"), {"cmd": (None, "")}, BEFORE).status == "HUMAN"
    assert judge(item("HUMAN"), {"cmd": (0, "")}, BEFORE).status == "PASS"


# The counts line, the order and the exit code


def test_the_counts_line_is_exact() -> None:
    it = item()
    outcomes = [dc.Outcome(it, s) for s in ("PASS", "RED", "RED", "BLOCKED", "HUMAN", "HUMAN")]
    assert dc.counts_line(outcomes) == "RED: 2 BLOCKED: 1 HUMAN: 2"
    assert dc.counts_line([]) == "RED: 0 BLOCKED: 0 HUMAN: 0"


def test_lines_come_in_file_order_even_when_run_together(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "here").write_text("x")
    text = table(
        row("D01", "sleep 0.4 && test -f here"),
        row("D02", "test -f missing"),
        row("D03", "test -f here"),
    )
    code, lines = run_main(tmp_path, capsys, text)
    marks = [ln.split()[:2] for ln in lines[1:-1]]
    assert marks == [["PASS", "D01"], ["RED", "D02"], ["PASS", "D03"]]
    assert lines[-1] == "RED: 1 BLOCKED: 0 HUMAN: 0"
    assert code == 1


def test_exit_code_is_0_when_only_blocked_and_human_are_left(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "here").write_text("x")
    text = table(
        row("D01", "test -f here"),
        row("D02", "test -f missing", "DATED", "2026-09-28T01:00:00Z"),
        row("D03", "test -f missing", "HUMAN"),
        row("D04", "test -f missing", "BLOCKED-IF", cause="their DNS", cause_test="test -f here"),
    )
    code, lines = run_main(tmp_path, capsys, text, "--now", "2026-09-24T06:00:00Z")
    assert lines[-1] == "RED: 0 BLOCKED: 2 HUMAN: 1"
    assert code == 0


def test_the_same_dated_item_is_red_after_its_date(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    text = table(row("D01", "test -f missing", "DATED", "2026-09-28T01:00:00Z"))
    code, lines = run_main(tmp_path, capsys, text, "--now", "2026-09-28T01:00:00Z")
    assert lines[-1] == "RED: 1 BLOCKED: 0 HUMAN: 0" and code == 1


def test_a_real_timeout_kills_the_command_and_counts_red(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    text = table(row("D01", "sleep 30 && test -f here"), row("D02", "bash -c 'sleep 30'"))
    start = time.monotonic()
    code, lines = run_main(tmp_path, capsys, text, "--timeout", "1")
    assert time.monotonic() - start < 15
    assert lines[1].startswith("RED      D01") and "ran past 1 s" in lines[1]
    assert lines[2].startswith("RED      D02")
    assert lines[-1] == "RED: 2 BLOCKED: 0 HUMAN: 0" and code == 1


def test_commands_run_from_the_root_under_pipefail(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "here").write_text("x")
    text = table(row("D01", "test -f here"), row("D02", "false | cat"))
    code, lines = run_main(tmp_path, capsys, text)
    assert lines[1].startswith("PASS") and lines[2].startswith("RED")


def test_a_malformed_checklist_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, lines = run_main(tmp_path, capsys, table(row("D01", "true")))
    assert code == 2 and "cannot fail" in lines[-1]


def test_only_picks_items_and_refuses_an_unknown_id(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    text = table(row("D01", "test -f missing"), row("D02", "test -d ."))
    code, lines = run_main(tmp_path, capsys, text, "--only", "D02")
    assert code == 0 and lines[-1] == "RED: 0 BLOCKED: 0 HUMAN: 0"
    code, lines = run_main(tmp_path, capsys, text, "--only", "D09")
    assert code == 2


# The real checklist


INTERNAL = ROOT.joinpath("docs", "internal")


@pytest.mark.skipif(not INTERNAL.is_dir(), reason="the working notes were removed at go-public")
def test_the_real_checklist_reads_and_every_command_names_real_parts() -> None:
    items = dc.parse(dc.DONE_FILE.read_text(encoding="utf-8"))
    kinds = {i.kind for i in items}
    assert kinds == set(dc.KINDS)
    targets = done_items.make_targets(ROOT)
    for it in items:
        for cmd in (it.command, it.cause_test):
            for name in re.findall(r"done_items\.py\s+([a-z-]+)", cmd):
                assert name in done_items.CHECKS, (
                    f"{it.id} runs a check that does not exist: {name}"
                )
            for target in re.findall(r"\bmake\s+(?:-n\s+)?([a-z][a-z0-9-]*)", cmd):
                assert target in targets, f"{it.id} runs make {target}, which the Makefile lacks"
            for path in re.findall(r"\b(scripts/[a-z_]+\.py|scripts/tests/[a-z_]+\.py)\b", cmd):
                assert (ROOT / path).is_file(), f"{it.id} runs {path}, which does not exist"
    humans = [i for i in items if i.kind == "HUMAN"]
    assert len(humans) == done_items.human_count(ROOT) and humans


@pytest.mark.skipif(not INTERNAL.is_dir(), reason="the working notes were removed at go-public")
def test_the_real_checklist_keeps_the_order_of_update_27() -> None:
    text = dc.DONE_FILE.read_text(encoding="utf-8")
    groups = [ln[3:] for ln in text.splitlines() if ln.startswith("## ")]
    wanted = ["UPDATE_22", "Block 23", "Block 24", "Hardening", "submission", "Dated", "Human"]
    at = [next(i for i, g in enumerate(groups) if w.lower() in g.lower()) for w in wanted]
    assert at == sorted(at)
    # UPDATE_29 asks for its lines at the end of the file, after the human items, as a last block
    # of its own; within UPDATE_27's part the human items still come last.
    head = text.split("\n## UPDATE_29", 1)[0]
    kinds = [i.kind for i in dc.parse(head)]
    first_human = kinds.index("HUMAN")
    assert set(kinds[first_human:]) == {"HUMAN"}, "the human items come last"


def run_cause_test(tmp_path: Path, name: str, lookup: str | None) -> int:
    """The D41 cause test's exit code, run as done-check runs it, with lookup deciding what the
    stand-in python3 does: None leaves python3 missing; "fails" raises socket.gaierror as for a
    name that does not resolve; "works" returns an address. No lookup leaves this machine."""
    items = {i.id: i for i in dc.parse(dc.DONE_FILE.read_text(encoding="utf-8"))}
    command = items["D41"].cause_test
    assert "sandbox.hl7europe.eu" in command
    folder = tmp_path / name
    (folder / "bin").mkdir(parents=True)
    env = {"PATH": str(folder / "bin")}
    if lookup is not None:
        (folder / "bin" / "python3").symlink_to(sys.executable)
        answer = (
            "raise socket.gaierror(8, 'nodename nor servname provided, or not known')"
            if lookup == "fails"
            else "return [(2, 1, 6, '', ('192.0.2.1', 443))]"
        )
        (folder / "sitecustomize.py").write_text(
            f"import socket\n\n\ndef getaddrinfo(*args, **kwargs):\n    {answer}\n\n\n"
            "socket.getaddrinfo = getaddrinfo\n"
        )
        env["PYTHONPATH"] = str(folder)
    bash = shutil.which("bash") or "/bin/bash"
    proc = subprocess.run(
        [bash, "-o", "pipefail", "-c", command], env=env, capture_output=True, timeout=60
    )
    return proc.returncode


@pytest.mark.skipif(not INTERNAL.is_dir(), reason="the working notes were removed at go-public")
def test_the_d41_cause_holds_only_while_the_name_does_not_resolve(tmp_path: Path) -> None:
    # REVIEW_03 R59: the cause test began with !, which turned "python3: command not found" (127)
    # into 0, so D41 would have stayed BLOCKED with no lookup made at all.
    assert run_cause_test(tmp_path, "gone", "fails") == 0
    assert run_cause_test(tmp_path, "back", "works") != 0
    assert run_cause_test(tmp_path, "missing", None) != 0
