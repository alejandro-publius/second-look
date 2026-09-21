"""Follow-up selection: one test per rule firing and not firing, the cap, unknown rain, priority."""

from __future__ import annotations

import copy
from datetime import date
from pathlib import Path
from typing import Any

import yaml
from hypothesis import given, settings
from hypothesis import strategies as st

from core.followups import Followup, SiteContext, select_followups
from core.gate import Flag
from core.records import FEATURES, FeatureScore, Observer

ROOT = Path(__file__).resolve().parents[2]
TABLE: dict[str, Any] = yaml.safe_load((ROOT / "content" / "followups.yaml").read_text("utf-8"))
FORM_ITEMS: list[dict[str, Any]] = yaml.safe_load(
    (ROOT / "content" / "form.yaml").read_text("utf-8")
)["items"]

DRY = SiteContext(rain="dry", dry_days=3, mm_in_window=0.4)
WET = SiteContext(rain="wet", dry_days=0, mm_in_window=12.0)
UNKNOWN = SiteContext(rain="unknown")
FLAG = Flag(feature="artificial_bank", confidence=0.9, note="a built edge on the left bank")
Answers = dict[str, str | float | list[str]]


def observer(**correct: int) -> Observer:
    return Observer(
        contributor_token="ct-test-observer-01",
        scores=tuple(
            FeatureScore(feature=f, correct=c, tested_on=date(2026, 9, 21))  # type: ignore[arg-type]
            for f, c in correct.items()
        ),
    )


def run(
    answers: Answers,
    site: SiteContext = DRY,
    obs: Observer | None = None,
    flags: tuple[Flag, ...] = (),
    *,
    checker_enabled: bool = False,
    table: dict[str, Any] = TABLE,
    form_items: list[dict[str, Any]] = FORM_ITEMS,
) -> list[Followup]:
    return select_followups(
        answers, site, obs, flags, table, form_items=form_items, checker_enabled=checker_enabled
    )


def rule_ids(chosen: list[Followup]) -> list[str]:
    return [c.rule_id for c in chosen]


def test_table_matches_the_content_file() -> None:
    assert TABLE["max_questions"] == 2
    assert [r["id"] for r in sorted(TABLE["rules"], key=lambda r: r["priority"])] == [
        "dry_pipe",
        "rating_check",
        "checker_flag",
        "low_score",
    ]


def test_dry_pipe_fires_when_a_pipe_is_present_and_it_is_dry() -> None:
    chosen = run({"draining_pipes": "present"}, DRY)
    assert chosen == [
        Followup(
            rule_id="dry_pipe", kind="yesno", question_key="followup.dry_pipe", params={"days": 3}
        )
    ]


def test_dry_pipe_fires_on_a_sewage_sign_too() -> None:
    assert rule_ids(run({"sewage_discharge": "present"}, DRY)) == ["dry_pipe"]


def test_dry_pipe_does_not_fire_without_a_pipe_or_when_wet() -> None:
    assert run({"draining_pipes": "absent", "sewage_discharge": "cant_tell"}, DRY) == []
    assert run({"draining_pipes": "present"}, WET) == []
    assert run({}, DRY) == []


def test_dry_pipe_does_not_fire_without_a_day_count() -> None:
    assert run({"draining_pipes": "present"}, SiteContext(rain="dry", dry_days=None)) == []
    assert run({"draining_pipes": "present"}, SiteContext(rain="dry", dry_days=0)) == []


@settings(max_examples=100, deadline=None)
@given(
    pipes=st.sampled_from(["present", "absent", "cant_tell"]),
    sewage=st.sampled_from(["present", "absent", "cant_tell"]),
    dry_days=st.none() | st.integers(0, 30),
    mm=st.none() | st.floats(min_value=0, max_value=100),
)
def test_unknown_rain_never_fires_dry_pipe(
    pipes: str, sewage: str, dry_days: int | None, mm: float | None
) -> None:
    site = SiteContext(rain="unknown", dry_days=dry_days, mm_in_window=mm)
    chosen = run({"draining_pipes": pipes, "sewage_discharge": sewage}, site)
    assert "dry_pipe" not in rule_ids(chosen)


def test_rating_check_fires_with_labels_from_the_form() -> None:
    chosen = run(
        {"overall_rating": "good", "bank_type": "present", "invasive_species": "present"}, WET
    )
    assert rule_ids(chosen) == ["rating_check"]
    assert chosen[0].kind == "keep_rating"
    assert chosen[0].question_key == "followup.rating_check"
    issues = str(chosen[0].params["issues"])
    # content/form.yaml now carries short labels for these items, so the plain phrases win.
    assert issues == "artificial banks, invasive plants"
    assert chosen[0].params["first_rating"] == "good"


def test_rating_check_prefers_a_short_label_when_the_content_carries_one() -> None:
    items = copy.deepcopy(FORM_ITEMS)
    for item in items:
        if item["id"] == "impervious_left":
            item["short_label"] = "a paved left margin"
    chosen = run({"overall_rating": "good", "impervious_left": "present"}, WET, form_items=items)
    assert chosen[0].params["issues"] == "a paved left margin"


def test_rating_check_does_not_fire_without_a_good_rating_or_without_an_issue() -> None:
    assert run({"overall_rating": "moderate", "bank_type": "present"}, WET) == []
    assert run({"overall_rating": "good"}, WET) == []
    assert (
        run({"overall_rating": "good", "bank_type": "absent", "invasive_species": "cant_tell"}, WET)
        == []
    )
    assert run({"bank_type": "present"}, WET) == []


def test_checker_flag_fires_only_when_enabled_and_a_flag_exists() -> None:
    chosen = run({}, WET, flags=(FLAG,), checker_enabled=True)
    assert chosen == [
        Followup(
            rule_id="checker_flag",
            kind="look_again",
            question_key="followup.checker_flag",
            params={"note": FLAG.note, "feature": "artificial_bank"},
        )
    ]


def test_checker_flag_does_not_fire_when_disabled_or_without_flags() -> None:
    assert run({}, WET, flags=(FLAG,), checker_enabled=False) == []
    assert run({}, WET, flags=(), checker_enabled=True) == []


def test_checker_flag_is_at_most_one_and_takes_the_surest_flag() -> None:
    other = Flag(feature="invasive_plant", confidence=0.95, note="a stand of tall reed")
    chosen = run({}, WET, flags=(FLAG, other), checker_enabled=True)
    assert rule_ids(chosen) == ["checker_flag"]
    assert chosen[0].params["note"] == "a stand of tall reed"


def test_checker_flag_uses_one_of_the_two_slots() -> None:
    chosen = run(
        {"draining_pipes": "present", "bank_type": "absent"},
        DRY,
        observer(artificial_bank=1),
        flags=(FLAG,),
        checker_enabled=True,
    )
    assert rule_ids(chosen) == ["dry_pipe", "checker_flag"]


def test_low_score_fires_on_a_weak_score_and_an_absent_answer() -> None:
    chosen = run({"bank_type": "absent"}, WET, observer(artificial_bank=2))
    assert chosen == [
        Followup(
            rule_id="low_score",
            kind="photo",
            question_key="followup.low_score",
            params={
                "feature": "artificial bank",
                "feature_id": "artificial_bank",
                "item_id": "bank_type",
                "correct": 2,
            },
        )
    ]


def test_low_score_picks_the_weakest_feature_first() -> None:
    chosen = run(
        {"bank_type": "absent", "invasive_species": "absent"},
        WET,
        observer(artificial_bank=2, invasive_plant=0),
    )
    assert rule_ids(chosen) == ["low_score"]
    assert chosen[0].params["feature_id"] == "invasive_plant"
    assert chosen[0].params["correct"] == 0


def test_low_score_does_not_fire_on_a_pass_or_a_present_answer_or_no_score() -> None:
    assert run({"bank_type": "absent"}, WET, observer(artificial_bank=3)) == []
    assert run({"bank_type": "present"}, WET, observer(artificial_bank=1)) == []
    assert run({"bank_type": "cant_tell"}, WET, observer(artificial_bank=1)) == []
    assert run({"bank_type": "absent"}, WET, observer(invasive_plant=1)) == []
    assert run({"bank_type": "absent"}, WET, None) == []


def test_cap_is_two_even_when_every_rule_fires() -> None:
    answers: Answers = {
        "draining_pipes": "present",
        "overall_rating": "good",
        "bank_type": "absent",
        "sewage_discharge": "present",
    }
    chosen = run(answers, DRY, observer(artificial_bank=1), flags=(FLAG,), checker_enabled=True)
    assert rule_ids(chosen) == ["dry_pipe", "rating_check"]
    bigger = copy.deepcopy(TABLE)
    bigger["max_questions"] = 4
    chosen = run(
        answers, DRY, observer(artificial_bank=1), flags=(FLAG,), checker_enabled=True, table=bigger
    )
    assert rule_ids(chosen) == ["dry_pipe", "rating_check", "checker_flag", "low_score"]


def test_priority_order_comes_from_the_table() -> None:
    answers: Answers = {
        "draining_pipes": "present",
        "overall_rating": "good",
        "bank_type": "absent",
    }
    flipped = copy.deepcopy(TABLE)
    for rule in flipped["rules"]:
        rule["priority"] = 10 - rule["priority"]
    chosen = run(
        answers,
        DRY,
        observer(artificial_bank=1),
        flags=(FLAG,),
        checker_enabled=True,
        table=flipped,
    )
    assert rule_ids(chosen) == ["low_score", "checker_flag"]


def test_unknown_rule_ids_are_ignored_and_a_zero_cap_asks_nothing() -> None:
    table = copy.deepcopy(TABLE)
    table["rules"].append({"id": "ask_the_model", "priority": 0, "question_key": "x"})
    assert rule_ids(run({"draining_pipes": "present"}, DRY, table=table)) == ["dry_pipe"]
    table["max_questions"] = 0
    assert run({"draining_pipes": "present"}, DRY, table=table) == []


def test_pure_same_inputs_same_output_and_inputs_untouched() -> None:
    answers: Answers = {
        "draining_pipes": "present",
        "overall_rating": "good",
        "bank_type": "present",
    }
    before = copy.deepcopy(answers)
    first = run(answers, DRY)
    second = run(answers, DRY)
    assert first == second
    assert answers == before


answer_value = st.sampled_from(["present", "absent", "cant_tell", "good", "moderate", "poor", ""])
answer_sets = st.dictionaries(
    st.sampled_from([i["id"] for i in FORM_ITEMS]), answer_value, max_size=10
)
flag_lists = st.lists(
    st.builds(
        Flag,
        feature=st.sampled_from(FEATURES),
        confidence=st.floats(0, 1),
        note=st.text(min_size=1, max_size=40).filter(lambda s: s.strip() and s.isprintable()),
    ),
    max_size=3,
)
observers = st.fixed_dictionaries({f: st.none() | st.integers(0, 4) for f in FEATURES}).map(
    lambda m: observer(**{f: c for f, c in m.items() if c is not None})
)
sites = st.builds(
    SiteContext,
    rain=st.sampled_from(["dry", "wet", "unknown"]),
    dry_days=st.none() | st.integers(0, 4),
    mm_in_window=st.none() | st.floats(0, 50),
)


@settings(max_examples=200, deadline=None)
@given(answers=answer_sets, flags=flag_lists, obs=observers, site=sites, enabled=st.booleans())
def test_flags_only_ever_add_the_checker_question(
    answers: Answers, flags: list[Flag], obs: Observer, site: SiteContext, enabled: bool
) -> None:
    with_flags = run(answers, site, obs, tuple(flags), checker_enabled=enabled)
    without = run(answers, site, obs, (), checker_enabled=enabled)
    assert len(with_flags) <= TABLE["max_questions"]
    assert len({c.rule_id for c in with_flags}) == len(with_flags)
    checker = [c for c in with_flags if c.rule_id == "checker_flag"]
    assert len(checker) <= 1
    if checker:
        assert enabled and flags
    rest = [c for c in with_flags if c.rule_id != "checker_flag"]
    assert rest == without[: len(rest)]
