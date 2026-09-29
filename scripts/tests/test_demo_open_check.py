"""apps/web/scripts/demo-open-check.mjs: what the heading of a judge mode page means.

The lock job runs the script with no flag and needs judge mode open. After the deploy that shuts
judge mode again (UPDATE_33) the same script is run with --expect shut. The helper is imported by
Node, so nothing here opens a browser or touches the network.
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
SCRIPT = ROOT / "apps" / "web" / "scripts" / "demo-open-check.mjs"
WORDS = json.loads((ROOT / "content" / "locales" / "en.json").read_text(encoding="utf-8"))
LIVE = "https://second-look-79t.pages.dev"


def node(*args: str) -> subprocess.CompletedProcess[str]:
    if shutil.which("node") is None:
        pytest.skip("needs node")
    env = {k: v for k, v in os.environ.items() if k != "DEMO_URL"}
    return subprocess.run(
        ["node", *args], capture_output=True, text=True, timeout=60, check=False, env=env
    )


def verdict(heading: str, url: str, expect: str) -> Any:
    body = (
        f"const m = await import({json.dumps(SCRIPT.as_uri())});\n"
        f"process.stdout.write(JSON.stringify(m.verdict({json.dumps(heading)}, "
        f"{json.dumps(url)}, {json.dumps(expect)}, {json.dumps(WORDS)})));"
    )
    done = node("--input-type=module", "-e", body)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def test_with_no_flag_only_the_open_page_passes() -> None:
    url = f"{LIVE}/demo"
    assert verdict(WORDS["demo.title"], url, "open") == {
        "state": "open",
        "pass": True,
        "said": "judge mode is open",
    }
    assert verdict(WORDS["demo.shut_title"], url, "open") == {
        "state": "shut",
        "pass": False,
        "said": "judge mode is still shut",
    }
    assert verdict("Not found", url, "open")["pass"] is False
    assert verdict("", url, "open")["pass"] is False


def test_expect_shut_passes_only_on_the_shut_page() -> None:
    url = f"{LIVE}/demo"
    assert verdict(WORDS["demo.shut_title"], url, "shut") == {
        "state": "shut",
        "pass": True,
        "said": "judge mode is shut",
    }
    assert verdict(WORDS["demo.title"], url, "shut")["pass"] is False
    other = verdict("Not found", url, "shut")
    assert other == {"state": "other", "pass": False, "said": "not the judge mode page"}
    # The heading the page had until UPDATE_33 is not the shut page any more.
    assert verdict("Judge mode opens on Sep 28", url, "shut")["pass"] is False


def test_part_2_has_its_own_open_heading() -> None:
    for url in (f"{LIVE}/t2/demo", f"{LIVE}/t2/demo/", "http://localhost:3221/t2/demo?x=1"):
        assert verdict(WORDS["part2.demo_title"], url, "open")["pass"] is True, url
        assert verdict(WORDS["demo.title"], url, "open")["pass"] is False, url
        assert verdict(WORDS["demo.shut_title"], url, "shut")["pass"] is True, url
    assert verdict(WORDS["part2.demo_title"], f"{LIVE}/demo", "open")["pass"] is False


def test_a_wrong_expect_stops_before_any_browser_opens() -> None:
    done = node(str(SCRIPT), "--expect", "maybe")
    assert done.returncode != 0
    assert "--expect takes open or shut, not maybe" in done.stderr
    assert "demo-open-check:" not in done.stdout


def test_the_flag_reader_takes_the_value_after_the_flag() -> None:
    body = (
        f"const m = await import({json.dumps(SCRIPT.as_uri())});\n"
        "process.stdout.write(JSON.stringify(["
        "m.flag(['node', 's', '--expect', 'shut'], '--expect'), "
        "m.flag(['node', 's'], '--expect'), "
        "m.flag(['node', 's', '--expect'], '--expect'), "
        "m.flag(['node', 's', '--clock', '2026-10-04T00:00:00Z', '--expect', 'open'], '--clock')"
        "]));"
    )
    done = node("--input-type=module", "-e", body)
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout) == ["shut", None, None, "2026-10-04T00:00:00Z"]
