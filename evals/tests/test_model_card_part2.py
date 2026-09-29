"""What docs/MODEL_CARD.md says about part 2, held to the committed flags and the code.

The card once said the models are only measured, while part 2 shows people a question built from
a model's stored answers. These tests fail if the card stops saying where that happens, or if a
sentence it states about the flags stops being true of results/assist_flags.json.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml

from core import assist
from evals import assist_flags as af

ROOT = Path(__file__).resolve().parents[2]
CARD = ROOT / "docs" / "MODEL_CARD.md"
HEADING = "Part 2, where people meet the checker's question"
CHECKER_NAMES = {"claude-opus-5-5": "Claude Opus 5.5"}


def section(card: str, heading: str) -> str:
    """The text under one second level heading of the card, up to the next one."""
    _, found, rest = card.partition(f"\n## {heading}\n")
    assert found, f"docs/MODEL_CARD.md has no section named {heading!r}"
    return rest.split("\n## ", 1)[0]


def one_line(text: str) -> str:
    return " ".join(text.split())


def flags_against_gold(entries: Sequence[Mapping[str, Any]], gold: Mapping[str, str]) -> list[str]:
    """The item ids whose kept flag points away from that item's gold label. Pure."""
    wrong = []
    for e in entries:
        flag = e.get("flag")
        if isinstance(flag, Mapping) and flag.get("points_to") != gold.get(str(e["item_id"])):
            wrong.append(str(e["item_id"]))
    return wrong


def committed() -> tuple[dict[str, Any], dict[str, str]]:
    flags = json.loads((ROOT / "results" / "assist_flags.json").read_text(encoding="utf-8"))
    items = yaml.safe_load((ROOT / "content" / "part2_items.yaml").read_text(encoding="utf-8"))
    return flags, {str(i["id"]): str(i["gold"]) for i in items["items"]}


def test_a_flag_that_points_away_from_the_gold_label_is_found() -> None:
    gold = {"a": "present", "b": "absent", "c": "present"}
    entries: list[dict[str, Any]] = [
        {"item_id": "a", "flag": {"points_to": "present"}},
        {"item_id": "b", "flag": {"points_to": "present"}},
        {"item_id": "c", "flag": None},
    ]
    assert flags_against_gold(entries, gold) == ["b"]


def test_every_part_2_flag_points_the_way_of_the_gold_label() -> None:
    """The card says so, and says part 2 cannot show what a wrong flag does. If the flags are ever
    made again and one is wrong, that sentence in the card has to change with them."""
    flags, gold = committed()
    kept = [e for e in flags["items"] if e["flag"] is not None]
    assert kept, "no kept flag to check"
    assert len(kept) == flags["n_flags"]
    assert flags_against_gold(flags["items"], gold) == []


def test_the_photos_with_no_flag_are_the_plant_photos() -> None:
    flags, _ = committed()
    bare = [e for e in flags["items"] if e["flag"] is None]
    assert {e["feature"] for e in bare} == {"invasive_plant"}
    reasons = sorted(str(e["reason"]) for e in bare)
    assert len(reasons) == 2
    assert "not passed by model" in reasons[0]
    assert reasons[1] == "the model's answer was cant_tell"


def test_the_card_has_a_section_on_part_2_that_names_its_sources() -> None:
    flags, _ = committed()
    text = section(CARD.read_text(encoding="utf-8"), HEADING)
    flat = one_line(text)
    for needed in (
        "`/t2`",
        "`evals/assist_flags.py`",
        "`results/assist_flags.json`",
        f"`{flags['answers_file']}`",
        "`worker/src/part2.ts`",
        "`docs/analysis_plan_v2.md`",
        "<!--v:results/assist_flags.json#/n_flags-->",
        f'"{assist.QUESTION}"',
        CHECKER_NAMES[flags["checker_model"]],
        "No model is called while a person answers",
        "points the way of the gold label",
    ):
        assert needed in flat, f"the part 2 section of the model card does not say: {needed}"


def test_the_rule_the_card_states_is_the_rule_the_script_uses() -> None:
    flags, _ = committed()
    answers = json.loads((ROOT / flags["answers_file"]).read_text(encoding="utf-8"))
    flat = one_line(section(CARD.read_text(encoding="utf-8"), HEADING))
    assert f"at least {af.MAJORITY} of its {answers['runs']} runs" in flat


def test_the_card_does_not_say_the_models_are_only_measured_everywhere() -> None:
    """The sentence about where the models are only measured has to name part 2 before it."""
    flat = one_line(CARD.read_text(encoding="utf-8"))
    before, found, _ = flat.partition("Everywhere else the models are only measured")
    assert found, "the card no longer says where the models are only measured"
    where = before.rpartition("Where it runs today")[2]
    assert "Part 2 of the test shows people a question" in where
