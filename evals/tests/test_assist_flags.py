"""Part 2 flags: only a feature the checker passed can ever produce one (UPDATE_31 section 2)."""

from __future__ import annotations

import json
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from core.records import FEATURES
from evals import assist_flags as af

ROOT = Path(__file__).resolve().parents[2]
MODEL = "claude-opus-5-5"
ANSWERS = st.sampled_from(["yes", "no", "cant_tell", "", "maybe"])


def table(passed: dict[str, bool], *, real: bool = True) -> dict[str, object]:
    return {"real": real, "models": {MODEL: {f: {"passed": p} for f, p in passed.items()}}}


def answers(said: list[str], note: object = "a pipe on the left") -> list[dict[str, object]]:
    return [{"model": MODEL, "answer": a, "note": note} for a in said]


@settings(max_examples=400, deadline=None)
@given(
    feature=st.sampled_from(sorted(FEATURES)),
    passed=st.fixed_dictionaries({f: st.booleans() for f in sorted(FEATURES)}),
    real=st.booleans(),
    said=st.lists(ANSWERS, min_size=0, max_size=5),
    note=st.one_of(st.text(max_size=300), st.none(), st.integers()),
)
def test_a_feature_the_model_did_not_pass_never_produces_a_flag(
    feature: str, passed: dict[str, bool], real: bool, said: list[str], note: object
) -> None:
    entry = af.flag_for_item(
        "a01", feature, answers(said, note), model_id=MODEL, pass_table=table(passed, real=real)
    )
    if entry["flag"] is not None:
        assert passed[feature] is True
        assert real is True
        assert entry["flag"]["points_to"] in {"present", "absent"}
        assert set(entry["flag"]) == {"points_to", "confidence", "note"}


def test_passed_feature_with_a_clear_majority_is_flagged() -> None:
    entry = af.flag_for_item(
        "a07",
        "pipe_running",
        answers(["yes", "yes", "no"]),
        model_id=MODEL,
        pass_table=table(dict.fromkeys(FEATURES, True)),
    )
    assert entry["flag"] == {
        "points_to": "present",
        "confidence": 0.6667,
        "note": "a pipe on the left",
    }


def test_not_passed_is_dropped_with_the_gates_reason() -> None:
    entry = af.flag_for_item(
        "a05",
        "invasive_plant",
        answers(["yes", "yes", "yes"]),
        model_id=MODEL,
        pass_table=table({**dict.fromkeys(FEATURES, True), "invasive_plant": False}),
    )
    assert entry["flag"] is None
    assert "not passed" in entry["reason"]


def test_cant_tell_or_split_runs_give_no_flag() -> None:
    full = table(dict.fromkeys(FEATURES, True))
    for said in (["cant_tell"] * 3, ["yes", "no", "cant_tell"], []):
        entry = af.flag_for_item(
            "a01", "artificial_bank", answers(said), model_id=MODEL, pass_table=full
        )
        assert entry["flag"] is None


def test_a_synthetic_pass_table_licenses_nothing() -> None:
    entry = af.flag_for_item(
        "a01",
        "artificial_bank",
        answers(["yes"] * 3),
        model_id=MODEL,
        pass_table=table(dict.fromkeys(FEATURES, True), real=False),
    )
    assert entry["flag"] is None


def test_committed_flags_match_the_committed_pass_table() -> None:
    """Every committed flag is on a feature the checker passed in the committed table."""
    path = ROOT / "results" / "assist_flags.json"
    if not path.exists():
        return
    doc = json.loads(path.read_text(encoding="utf-8"))
    pass_table = json.loads((ROOT / "results" / "model_pass_table.json").read_text("utf-8"))
    row = pass_table["models"][doc["checker_model"]]
    assert len(doc["items"]) == 8
    for e in doc["items"]:
        if e["flag"] is not None:
            assert row[e["feature"]]["passed"] is True, e
    assert af.main(["--check"]) == 0


def test_part2_items_are_two_per_feature_one_each_way_on_unshown_photos() -> None:
    items, model = af.load_items(ROOT)
    assert model == MODEL
    assert len(items) == 8
    for f in FEATURES:
        golds = sorted(i.gold for i in items if i.feature == f)
        assert golds == ["absent", "present"], f
    assert len({i.photo_id for i in items}) == 8
