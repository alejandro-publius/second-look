"""The read-only phone check of production: its counts check and the walk it picks.

The helpers are imported from apps/web/scripts/live-readonly.mjs by Node with a fake fetch, so
nothing here opens a browser or touches the network.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "apps" / "web" / "scripts" / "live-readonly.mjs"


def node(*args: str) -> subprocess.CompletedProcess[str]:
    if shutil.which("node") is None:
        pytest.skip("needs node")
    env = {k: v for k, v in os.environ.items() if k not in ("SITE_URL", "API_URL", "WALK_ID")}
    return subprocess.run(
        ["node", *args], capture_output=True, text=True, timeout=60, check=False, env=env
    )


def call(expr: str) -> Any:
    """Evaluate expr with the script's exports as m, and return what it gives back."""
    body = (
        f"const m = await import({json.dumps(SCRIPT.as_uri())});\n"
        f"process.stdout.write(JSON.stringify(await ({expr})));"
    )
    done = node("--input-type=module", "-e", body)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def reply(ok: bool, status: int, body: Any) -> str:
    """A fake fetch that answers once with this status and JSON body."""
    return (
        f"async () => ({{ ok: {json.dumps(ok)}, status: {status}, "
        f"json: async () => ({json.dumps(body)}) }})"
    )


def test_a_reply_that_is_not_ok_is_a_failed_read_even_with_by_arm() -> None:
    got = call(f"m.readCounts('https://x', {reply(False, 503, {'by_arm': {'a': 1}})})")
    assert got == {"error": "HTTP 503"}


def test_a_reply_with_no_by_arm_is_a_failed_read() -> None:
    assert "error" in call(f"m.readCounts('https://x', {reply(True, 200, {})})")
    assert "error" in call(f"m.readCounts('https://x', {reply(True, 200, {'by_arm': None})})")
    assert "error" in call(f"m.readCounts('https://x', {reply(True, 200, None)})")


def test_a_fetch_that_throws_is_a_failed_read() -> None:
    got = call("m.readCounts('https://x', async () => { throw new Error('offline'); })")
    assert got == {"error": "Error: offline"}


def test_a_good_read_gives_the_counts() -> None:
    got = call(f"m.readCounts('https://x', {reply(True, 200, {'by_arm': {'a': 2}})})")
    assert got == {"value": '{"a":2}'}


def test_two_failed_reads_do_not_pass_the_counts_check() -> None:
    # They used to: JSON.stringify(undefined) twice compared equal.
    bad = {"error": "HTTP 500"}
    assert call(f"m.countsCheck({json.dumps(bad)}, {json.dumps(bad)})")["pass"] is False
    good = {"value": '{"a":1}'}
    assert call(f"m.countsCheck({json.dumps(good)}, {json.dumps(bad)})")["pass"] is False
    assert call(f"m.countsCheck({json.dumps(bad)}, {json.dumps(good)})")["pass"] is False


def test_the_counts_check_passes_only_when_the_counts_hold() -> None:
    same = {"value": '{"a":1}'}
    moved = {"value": '{"a":2}'}
    assert call(f"m.countsCheck({json.dumps(same)}, {json.dumps(same)})")["pass"] is True
    assert call(f"m.countsCheck({json.dumps(same)}, {json.dumps(moved)})")["pass"] is False


def test_walk_id_wins_then_the_first_built_walk_then_none(tmp_path: Path) -> None:
    content = tmp_path / "content.json"
    content.write_text(json.dumps({"walks": [{"id": "v02"}, {"id": "v03"}]}), encoding="utf-8")
    path = json.dumps(str(content))
    assert call(f"m.chooseWalk('v09', {path})") == {"id": "v09", "from": "WALK_ID"}
    got = call(f"m.chooseWalk('', {path})")
    assert got["id"] == "v02" and "generated/content.json" in got["from"]
    missing = json.dumps(str(tmp_path / "none.json"))
    assert call(f"m.chooseWalk('', {missing})") == {"id": "", "from": ""}
    (tmp_path / "empty.json").write_text('{"walks": []}', encoding="utf-8")
    empty = json.dumps(str(tmp_path / "empty.json"))
    assert call(f"m.chooseWalk('', {empty})") == {"id": "", "from": ""}


def test_run_as_a_script_it_still_asks_for_site_url() -> None:
    # Importing the helpers runs nothing, but running the file still runs the check.
    done = node(str(SCRIPT))
    assert done.returncode != 0
    assert "set SITE_URL" in done.stderr


def test_the_pick_list_creeks_come_from_every_region_in_the_build(tmp_path: Path) -> None:
    # UPDATE_30 section 1 item 4: the live check taps each creek on bare /city, so it reads them
    # from every region the web build holds, and names none when there is no build.
    content = tmp_path / "content.json"
    regions = {
        "a": {"creeks": [{"slug": "strawberry-creek", "name": "Strawberry Creek"}]},
        "b": {"creeks": []},
        "c": {"creeks": [{"slug": "other-creek", "name": "Other Creek"}]},
    }
    content.write_text(json.dumps({"regions": regions}), encoding="utf-8")
    assert call(f"m.pickListCreeks({json.dumps(str(content))})") == [
        {"slug": "strawberry-creek", "name": "Strawberry Creek"},
        {"slug": "other-creek", "name": "Other Creek"},
    ]
    assert call(f"m.pickListCreeks({json.dumps(str(tmp_path / 'none.json'))})") == []


def test_judge_mode_is_expected_shut_before_the_lock_and_open_from_it_on() -> None:
    """The lock job runs this check after the lock, when /demo is open. The check once waited for
    the shut page at any hour, so the job failed its own phone check on 2026-09-28."""
    from core.lock import DATA_LOCK_UTC

    words = json.loads((ROOT / "content" / "locales" / "en.json").read_text(encoding="utf-8"))
    lock = DATA_LOCK_UTC.strftime("%Y-%m-%dT%H:%M:%SZ")
    before = call("m.judgeModeExpected(new Date('2026-09-28T00:59:59Z'))")
    assert before == {
        "open": False,
        "name": "judge mode says when it opens",
        "heading": words["demo.shut_title"],
    }
    for moment in (lock, "2026-09-28T01:17:42Z", "2026-10-15T00:00:00Z"):
        after = call(f"m.judgeModeExpected(new Date({json.dumps(moment)}))")
        assert after["open"] is True, moment
        assert after["heading"] == words["demo.title"], moment
    # The two headings must differ by more than a prefix match would see.
    assert words["demo.title"] != words["demo.shut_title"]


def test_judge_mode_reads_the_lock_the_page_is_built_from(tmp_path: Path) -> None:
    from core.lock import DATA_LOCK_UTC

    page_lock = (ROOT / "apps" / "web" / "lib" / "lock.ts").read_text(encoding="utf-8")
    assert DATA_LOCK_UTC.strftime("%Y-%m-%dT%H:%M:%SZ") in page_lock
    # A lock file with no instant in it is an error, never a silent "open".
    empty = tmp_path / "lock.ts"
    empty.write_text("export const NOTHING = 1;\n", encoding="utf-8")
    body = (
        f"const m = await import({json.dumps(SCRIPT.as_uri())});\n"
        f"m.judgeModeExpected(new Date(), {json.dumps(str(empty))});"
    )
    done = node("--input-type=module", "-e", body)
    assert done.returncode != 0
    assert "no DATA_LOCK_UTC" in done.stderr
