"""The study's instants are written once in core/lock.py and copied where Python cannot reach.

The browser decides by apps/web/lib/lock.ts and the live API is the Worker, so judge mode opens
at the times those two hold, not at the time core/lock.py holds. Only tests that read every copy
keep them the same (UPDATE_33; review REVIEW_03 R52 for the first lock). The comparison the web
build runs is apps/web/scripts/lock-mirror.mjs, called by apps/web/scripts/design-check.mjs; it
is proved here on files made to differ.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from core import lock

ROOT = Path(__file__).resolve().parents[2]
MIRROR = ROOT / "apps" / "web" / "scripts" / "lock-mirror.mjs"
LOCK_PY = ROOT / "core" / "lock.py"
LOCK_TS = ROOT / "apps" / "web" / "lib" / "lock.ts"
WORKER_INDEX = ROOT / "worker" / "src" / "index.ts"
DESIGN_CHECK = ROOT / "apps" / "web" / "scripts" / "design-check.mjs"
SHUT_DETAIL = "Judge mode opens on Oct 3."


def iso(when: datetime) -> str:
    return when.strftime("%Y-%m-%dT%H:%M:%SZ")


def call(expr: str) -> Any:
    """Evaluate expr with lock-mirror.mjs's exports as m, and return what it gives back."""
    if shutil.which("node") is None:
        pytest.skip("needs node")
    body = (
        f"const m = await import({json.dumps(MIRROR.as_uri())});\n"
        f"process.stdout.write(JSON.stringify(await ({expr})));"
    )
    done = subprocess.run(
        ["node", "--input-type=module", "-e", body],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def fails(python_text: str, web_text: str) -> list[str]:
    return list(call(f"m.lockMirrorFails({json.dumps(python_text)}, {json.dumps(web_text)})"))


# The real files ---------------------------------------------------------------------------------


def test_the_web_copy_is_the_python_lock() -> None:
    py, ts = LOCK_PY.read_text(encoding="utf-8"), LOCK_TS.read_text(encoding="utf-8")
    assert fails(py, ts) == []
    # The check read the real values, not nothing on both sides.
    assert call(f"m.webLockConstants({json.dumps(ts)})") == {
        "DATA_LOCK_UTC": iso(lock.DATA_LOCK_UTC),
        "DATA_LOCK_LOCAL_LABEL": lock.DATA_LOCK_LOCAL_LABEL,
        "WAVE2_OPEN_UTC": iso(lock.WAVE2_OPEN_UTC),
        "WAVE2_OPEN_LOCAL_LABEL": lock.WAVE2_OPEN_LOCAL_LABEL,
        "SECOND_LOCK_UTC": iso(lock.SECOND_LOCK_UTC),
        "SECOND_LOCK_LOCAL_LABEL": lock.SECOND_LOCK_LOCAL_LABEL,
        "JUDGE_MODE_OPENS_UTC": iso(lock.JUDGE_MODE_OPENS_UTC),
    }
    assert call(f"m.pythonLockConstants({json.dumps(py)})") == call(
        f"m.webLockConstants({json.dumps(ts)})"
    )


def test_the_design_gate_runs_the_comparison() -> None:
    # apps/web/lib/lock.ts says the design gate fails the build when the copies drift. Until
    # UPDATE_33 it said so and the gate held no such check.
    gate = DESIGN_CHECK.read_text(encoding="utf-8")
    assert "fails.push(...lockMirrorFails(" in gate
    assert "fails.push(...strayBeforeLockCallers(" in gate
    assert "design-check.mjs fails the build" in LOCK_TS.read_text(encoding="utf-8")


def worker_constant(name: str) -> datetime:
    found = re.findall(
        rf'^const {name} = Date\.parse\("([^"]+)"\);$',
        WORKER_INDEX.read_text(encoding="utf-8"),
        re.M,
    )
    assert len(found) == 1, f"worker/src/index.ts holds one {name}"
    return datetime.fromisoformat(found[0].replace("Z", "+00:00"))


def test_the_worker_opens_judge_mode_at_the_second_lock() -> None:
    assert worker_constant("JUDGE_MODE_OPENS_UTC") == lock.JUDGE_MODE_OPENS_UTC
    assert worker_constant("DATA_LOCK_UTC") == lock.DATA_LOCK_UTC


def test_both_judge_mode_routes_read_that_instant_and_nothing_else_does() -> None:
    text = WORKER_INDEX.read_text(encoding="utf-8")
    guard = (
        "if (lockClock(env) < JUDGE_MODE_OPENS_UTC) "
        f'return json(env, {{ detail: "{SHUT_DETAIL}" }}, 403);'
    )
    lines = text.splitlines()
    guards = [i for i, line in enumerate(lines) if line.strip() == guard]
    assert len(guards) == 2
    # Each guard is the first thing its route does.
    routes = [lines[i - 3].strip() for i in guards]
    assert routes == [
        'if (path === "/api/t2/demo" && request.method === "POST") {',
        'if (path === "/api/demo/answer" && request.method === "POST") {',
    ]
    # The constant, its comment and the two guards: no other line names it.
    named = [line for line in lines if "JUDGE_MODE_OPENS_UTC" in line]
    assert len(named) == 4, named
    # The first lock is read by the frozen createSession alone, for the post_lock mark.
    first = [line.strip() for line in lines if re.search(r"\bDATA_LOCK_UTC\b", line)]
    assert [line for line in first if not line.startswith("//")] == [
        'const DATA_LOCK_UTC = Date.parse("2026-09-28T01:00:00Z");',
        "Date.now() >= DATA_LOCK_UTC ? 1 : 0,",
    ]


def test_the_python_route_says_the_same_words() -> None:
    route = (ROOT / "apps" / "api" / "routes_study.py").read_text(encoding="utf-8")
    assert f'detail="{SHUT_DETAIL}"' in route
    day = f"{lock.JUDGE_MODE_OPENS_UTC:%b} {lock.JUDGE_MODE_OPENS_UTC.day}"
    assert f"Judge mode opens on {day}." == SHUT_DETAIL


@pytest.mark.parametrize("name", ["e2e.mjs", "part2_e2e.mjs"])
def test_the_worker_tests_stand_on_both_sides_of_the_instant(name: str) -> None:
    text = (ROOT / "worker" / "test" / name).read_text(encoding="utf-8")

    def constant(key: str) -> datetime:
        found = re.findall(rf'^const {key} = "([^"]+)";$', text, re.M)
        assert len(found) == 1, key
        return datetime.fromisoformat(found[0].replace("Z", "+00:00"))

    assert constant("FIRST_LOCK") == lock.DATA_LOCK_UTC
    assert constant("LOCK") == lock.JUDGE_MODE_OPENS_UTC
    before = constant("JUST_BEFORE_LOCK")
    assert (lock.JUDGE_MODE_OPENS_UTC - before).total_seconds() == 1
    # One second before the second lock is after the first: had the routes kept the first lock,
    # the shut side of these tests would find them open.
    assert before > lock.DATA_LOCK_UTC
    assert "E2E_NOW: JUST_BEFORE_LOCK" in text and "E2E_NOW: LOCK" in text


# The comparison, on files made to differ ------------------------------------------------------

PY = """DATA_LOCK_UTC = datetime(2026, 9, 28, 1, 0, 0, tzinfo=UTC)
DATA_LOCK_LOCAL_LABEL = "Sunday Sep 27, 2026 at 18:00 PDT"
WAVE2_OPEN_UTC = datetime(2026, 9, 30, 4, 0, 0, tzinfo=UTC)
WAVE2_OPEN_LOCAL_LABEL = "Tuesday Sep 29, 2026 at 21:00 PDT"
SECOND_LOCK_UTC = datetime(2026, 10, 3, 4, 0, 0, tzinfo=UTC)
SECOND_LOCK_LOCAL_LABEL = "Friday Oct 2, 2026 at 21:00 PDT"
JUDGE_MODE_OPENS_UTC = SECOND_LOCK_UTC
"""
TS = """export const DATA_LOCK_UTC = "2026-09-28T01:00:00Z";
export const DATA_LOCK_LOCAL_LABEL = "Sunday Sep 27, 2026 at 18:00 PDT";
export const WAVE2_OPEN_UTC = "2026-09-30T04:00:00Z";
export const WAVE2_OPEN_LOCAL_LABEL = "Tuesday Sep 29, 2026 at 21:00 PDT";
export const SECOND_LOCK_UTC = "2026-10-03T04:00:00Z";
export const SECOND_LOCK_LOCAL_LABEL = "Friday Oct 2, 2026 at 21:00 PDT";
export const JUDGE_MODE_OPENS_UTC = SECOND_LOCK_UTC;
"""


def test_two_files_that_agree_pass() -> None:
    assert fails(PY, TS) == []


def test_an_instant_that_differs_is_named_with_both_values() -> None:
    moved = TS.replace('SECOND_LOCK_UTC = "2026-10-03T04:00:00Z"', 'SECOND_LOCK_UTC = "X"')
    moved = moved.replace('"X"', '"2026-10-03T05:00:00Z"')
    got = fails(PY, moved)
    # Judge mode opens at the second lock, so it moved with it.
    assert got == [
        "apps/web/lib/lock.ts:1 SECOND_LOCK_UTC is 2026-10-03T05:00:00Z "
        "but core/lock.py says 2026-10-03T04:00:00Z",
        "apps/web/lib/lock.ts:1 JUDGE_MODE_OPENS_UTC is 2026-10-03T05:00:00Z "
        "but core/lock.py says 2026-10-03T04:00:00Z",
    ]


def test_judge_mode_tied_to_the_first_lock_again_is_a_fault() -> None:
    back = TS.replace(
        "JUDGE_MODE_OPENS_UTC = SECOND_LOCK_UTC", "JUDGE_MODE_OPENS_UTC = DATA_LOCK_UTC"
    )
    assert fails(PY, back) == [
        "apps/web/lib/lock.ts:1 JUDGE_MODE_OPENS_UTC is 2026-09-28T01:00:00Z "
        "but core/lock.py says 2026-10-03T04:00:00Z"
    ]


def test_a_label_that_differs_and_a_python_side_change_are_faults() -> None:
    label = TS.replace("Friday Oct 2, 2026 at 21:00 PDT", "Friday Oct 2, 2026 at 9 pm")
    assert len(fails(PY, label)) == 1 and "SECOND_LOCK_LOCAL_LABEL" in fails(PY, label)[0]
    python_moved = PY.replace("datetime(2026, 9, 30, 4, 0, 0", "datetime(2026, 9, 30, 4, 0, 1")
    got = fails(python_moved, TS)
    assert len(got) == 1 and "WAVE2_OPEN_UTC" in got[0] and "2026-09-30T04:00:01Z" in got[0]


def test_a_constant_that_one_file_lacks_is_a_fault() -> None:
    without = "\n".join(line for line in TS.splitlines() if "WAVE2_OPEN_UTC" not in line)
    assert fails(PY, without) == [
        "apps/web/lib/lock.ts:1 has no WAVE2_OPEN_UTC, or not in the form this check reads"
    ]
    py_without = "\n".join(line for line in PY.splitlines() if "JUDGE_MODE" not in line)
    assert fails(py_without, TS) == [
        "core/lock.py:1 has no JUDGE_MODE_OPENS_UTC, or not in the form this check reads"
    ]
    # Two empty files do not agree: they hold nothing.
    assert len(fails("", "")) == 14


def test_a_new_instant_in_one_file_only_is_a_fault() -> None:
    more = PY + "THIRD_LOCK_UTC = datetime(2026, 11, 1, 0, 0, 0, tzinfo=UTC)\n"
    assert fails(more, TS) == [
        "apps/web/lib/lock.ts:1 has no THIRD_LOCK_UTC, or not in the form this check reads"
    ]


def test_an_instant_that_is_not_a_time_is_a_fault() -> None:
    # The same wrong words on both sides agree with each other, and are still no time.
    py_bad = PY.replace(
        "WAVE2_OPEN_UTC = datetime(2026, 9, 30, 4, 0, 0, tzinfo=UTC)",
        'WAVE2_OPEN_UTC = "soon"',
    )
    ts_bad = TS.replace('WAVE2_OPEN_UTC = "2026-09-30T04:00:00Z"', 'WAVE2_OPEN_UTC = "soon"')
    assert fails(py_bad, ts_bad) == [
        "apps/web/lib/lock.ts:1 WAVE2_OPEN_UTC is soon, which is not a time"
    ]


def test_only_the_two_judge_mode_pages_may_call_is_before_lock() -> None:
    files = [
        {"path": "apps/web/app/demo/page.tsx", "text": "() => isBeforeLock(),"},
        {"path": "apps/web/app/t2/demo/page.tsx", "text": "() => isBeforeLock(),"},
        {"path": "apps/web/lib/lock.ts", "text": "export function isBeforeLock() {}"},
        {"path": "apps/web/app/t/page.tsx", "text": "const a = 1;\nif (isBeforeLock()) go();"},
        {"path": "apps/web/components/A.tsx", "text": "// isBeforeLock is named in a comment"},
        {"path": "apps/web/components/B.tsx", "text": "const isBeforeLocked = true;"},
    ]
    got = call(f"m.strayBeforeLockCallers({json.dumps(files)})")
    assert len(got) == 1
    assert got[0].startswith("apps/web/app/t/page.tsx:2 calls isBeforeLock")


def test_nothing_else_in_the_repo_calls_is_before_lock() -> None:
    # The name now answers whether judge mode is shut. Every file of the web app, its scripts
    # and its tests is read here, as the design gate reads them.
    found = []
    web = ROOT / "apps" / "web"
    for folder in ("app", "components", "lib", "scripts", "tests"):
        for path in sorted((web / folder).rglob("*")):
            if path.suffix not in {".ts", ".tsx", ".mjs", ".js", ".jsx"} or not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            code = [line for line in text.splitlines() if not re.match(r"^\s*(//|/?\*)", line)]
            if any(re.search(r"\bisBeforeLock\b", line) for line in code):
                found.append(path.relative_to(ROOT).as_posix())
    assert found == [
        "apps/web/app/demo/page.tsx",
        "apps/web/app/t2/demo/page.tsx",
        "apps/web/lib/lock.ts",
        # The check itself: it names the function to look for it, and calls nothing.
        "apps/web/scripts/lock-mirror.mjs",
    ]
