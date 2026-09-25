"""results/harden/costs.md says what results/cost_log.jsonl holds (critic round 15 N03).

It still said no paid model run had been logged, two days after the paid runs were, because
nothing compared it with the log. Now the committed files must be what the script makes of the
log today, apart from the time they were computed.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts import harden_costs as hc

FOLDER = hc.ROOT / "results" / "harden"
LOG = hc.ROOT / "results" / "cost_log.jsonl"


def committed() -> dict:
    return json.loads((FOLDER / "costs.json").read_text(encoding="utf-8"))


def test_the_committed_costs_are_what_the_log_gives_today() -> None:
    doc = committed()
    fresh = hc.summarize(hc.load(LOG), "results/cost_log.jsonl")
    assert {k: v for k, v in doc.items() if k != "checked_utc"} == fresh, (
        "results/harden/costs.json is older than results/cost_log.jsonl; run "
        "uv run python scripts/harden_costs.py"
    )


def test_the_committed_page_is_the_json_in_words() -> None:
    assert (FOLDER / "costs.md").read_text(encoding="utf-8") == hc.page(committed())


def test_real_lines_give_a_table_and_none_give_no_number(tmp_path: Path) -> None:
    real = {"real": True, "purpose": "footage", "model": "m", "cost_usd": 0.5}
    fake = {"real": False, "purpose": "benchmark", "model": "m", "cost_usd": 0.0}
    with_real = {"checked_utc": "t", **hc.summarize([real, real, fake], "log")}
    assert with_real["groups"][0]["calls"] == 2 and with_real["groups"][0]["per_100_usd"] == 50.0
    assert "| footage | m | 2 | 1.0 | 0.5 | 50.0 |" in hc.page(with_real)
    none = {"checked_utc": "t", **hc.summarize([fake], "log")}
    assert none["groups"] == [] and "No paid model run has been logged" in hc.page(none)
