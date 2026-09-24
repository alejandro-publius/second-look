"""Edges of the follow-up rules that mutation testing (make mutation) found no test for.

One dry day is enough for the pipe question; each question's text key comes from the content
table, and a table that leaves the key out still asks a question the locale has; and the low score
rule looks past every form item it cannot use instead of stopping at the first one.
"""

from __future__ import annotations

import copy
import json
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from core.followups import Followup, SiteContext, select_followups
from core.gate import Flag
from core.records import FeatureScore, Observer

ROOT = Path(__file__).resolve().parents[2]
TABLE: dict[str, Any] = yaml.safe_load((ROOT / "content" / "followups.yaml").read_text("utf-8"))
FORM_ITEMS: list[dict[str, Any]] = yaml.safe_load(
    (ROOT / "content" / "form.yaml").read_text("utf-8")
)["items"]
LOCALE: dict[str, str] = json.loads((ROOT / "content" / "locales" / "en.json").read_text("utf-8"))
FLAG = Flag(feature="artificial_bank", confidence=0.9, note="a built edge on the left bank")
EVERY_RULE_FIRES: dict[str, str | float | list[str]] = {
    "draining_pipes": "present",
    "overall_rating": "good",
    "bank_type": "absent",
    "sewage_discharge": "present",
}


def observer(**correct: int) -> Observer:
    return Observer(
        contributor_token="ct-test-observer-01",
        scores=tuple(
            FeatureScore(feature=f, correct=c, tested_on=date(2026, 9, 21))  # type: ignore[arg-type]
            for f, c in correct.items()
        ),
    )


def all_four(table: dict[str, Any]) -> list[Followup]:
    table = copy.deepcopy(table)
    table["max_questions"] = 4
    return select_followups(
        EVERY_RULE_FIRES,
        SiteContext(rain="dry", dry_days=3),
        observer(artificial_bank=1),
        (FLAG,),
        table,
        form_items=FORM_ITEMS,
        checker_enabled=True,
    )


def test_one_dry_day_is_enough_for_the_pipe_question_and_none_is_not() -> None:
    def ask(days: int) -> list[Followup]:
        return select_followups(
            {"draining_pipes": "present"},
            SiteContext(rain="dry", dry_days=days),
            None,
            (),
            TABLE,
            form_items=FORM_ITEMS,
        )

    chosen = ask(1)
    assert [c.rule_id for c in chosen] == ["dry_pipe"]
    assert chosen[0].params == {"days": 1}
    assert ask(0) == []


def test_each_question_key_comes_from_the_table() -> None:
    table = copy.deepcopy(TABLE)
    for rule in table["rules"]:
        rule["question_key"] = f"followup.v2.{rule['id']}"
    chosen = all_four(table)
    assert [c.rule_id for c in chosen] == ["dry_pipe", "rating_check", "checker_flag", "low_score"]
    assert [c.question_key for c in chosen] == [f"followup.v2.{c.rule_id}" for c in chosen]


def test_a_table_without_question_keys_still_asks_questions_the_locale_has() -> None:
    table = copy.deepcopy(TABLE)
    for rule in table["rules"]:
        rule.pop("question_key", None)
    chosen = all_four(table)
    assert [c.rule_id for c in chosen] == ["dry_pipe", "rating_check", "checker_flag", "low_score"]
    for c in chosen:
        assert c.question_key == f"followup.{c.rule_id}"
        assert c.question_key in LOCALE, c.question_key


def test_the_low_score_rule_looks_past_every_item_it_cannot_use() -> None:
    by_id = {item["id"]: item for item in FORM_ITEMS}
    # In this order: no feature at all, a feature answered present, a feature answered absent by
    # someone who passed it, and last the one that should be asked about.
    form = [
        by_id["water_flow"],
        by_id["bank_type"],
        by_id["draining_pipes"],
        by_id["invasive_species"],
    ]
    chosen = select_followups(
        {
            "water_flow": "slow",
            "bank_type": "present",
            "draining_pipes": "absent",
            "invasive_species": "absent",
        },
        SiteContext(rain="wet", dry_days=0),
        observer(artificial_bank=0, pipe_running=4, invasive_plant=1),
        (),
        TABLE,
        form_items=form,
    )
    assert [c.rule_id for c in chosen] == ["low_score"]
    assert chosen[0].params["item_id"] == "invasive_species"
    assert chosen[0].params["correct"] == 1
