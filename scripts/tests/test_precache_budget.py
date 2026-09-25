"""results/precache_budget.json: what a first visit downloads in the background (UPDATE_30 1.1).

make precache-budget writes it from apps/web/tests/offline-budget.spec.ts, which fails above the
budget in apps/web/offline-budget.mjs. These checks keep the committed number honest in make
check: under the budget, measured at a commit this repository has, and made with the offline
copies that are committed now, so new copies without a new measurement turn this red.
"""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from core import content_loader

ROOT = Path(__file__).resolve().parents[2]
RESULT = ROOT / "results" / "precache_budget.json"
BUDGET = ROOT / "apps" / "web" / "offline-budget.mjs"
# UPDATE_30 section 1 item 1: a first visit transfers no more than 3 MB in the background.
BRIEF_BUDGET_BYTES = 3_000_000


def result() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(RESULT.read_text(encoding="utf-8"))
    return data


def budget_in_code() -> int:
    found = re.search(r"BACKGROUND_BUDGET_BYTES = ([\d_]+);", BUDGET.read_text(encoding="utf-8"))
    assert found, f"no BACKGROUND_BUDGET_BYTES in {BUDGET}"
    return int(found.group(1).replace("_", ""))


def test_the_budget_in_the_code_is_the_briefs() -> None:
    assert budget_in_code() == BRIEF_BUDGET_BYTES


def test_the_recorded_first_visit_is_under_the_budget() -> None:
    r = result()
    assert r["budget_bytes"] == budget_in_code()
    assert 0 < r["bytes"] <= r["budget_bytes"]
    assert r["under_budget"] is True
    assert abs(r["megabytes"] - r["bytes"] / 1_000_000) <= 0.005
    assert r["cache_storage_bytes"] <= r["bytes"]
    assert r["files"] > r["photos"]["files"] > 0


def test_it_names_when_and_at_which_commit_it_was_measured() -> None:
    r = result()
    datetime.strptime(r["measured_at_utc"], "%Y-%m-%dT%H:%M:%SZ")
    assert re.fullmatch(r"[0-9a-f]{40}", r["commit"])
    found = subprocess.run(
        ["git", "cat-file", "-e", f"{r['commit']}^{{commit}}"], cwd=ROOT, capture_output=True
    )
    assert found.returncode == 0, f"{r['commit']} is not a commit of this repository"
    assert r["tree_clean"] is True


def test_it_measured_the_offline_copies_that_are_committed_now() -> None:
    rows = content_loader.offline_rows(ROOT)
    photos = result()["photos"]
    assert photos["files"] == len(rows)
    assert photos["bytes"] == sum(int(row["bytes"]) for row in rows)
