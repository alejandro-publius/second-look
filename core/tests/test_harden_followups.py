"""Follow-ups name each issue from form content in a fixed order and skip malformed table rules."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml
from hypothesis import given, settings
from hypothesis import strategies as st

from core.followups import Followup, SiteContext, select_followups

ROOT = Path(__file__).resolve().parents[2]
TABLE: dict[str, Any] = yaml.safe_load((ROOT / "content" / "followups.yaml").read_text("utf-8"))
FORM_ITEMS: list[dict[str, Any]] = yaml.safe_load(
    (ROOT / "content" / "form.yaml").read_text("utf-8")
)["items"]

DRY = SiteContext(rain="dry", dry_days=3, mm_in_window=0.4)
WET = SiteContext(rain="wet", dry_days=0, mm_in_window=12.0)
Answers = dict[str, str | float | list[str]]


def issues_for(answers: Answers, form_items: list[dict[str, Any]]) -> str:
    """Run the real table on a wet day, so only rating_check can fire, and return its issues."""
    chosen = select_followups(answers, WET, None, (), TABLE, form_items=form_items)
    assert [c.rule_id for c in chosen] == ["rating_check"]
    return str(chosen[0].params["issues"])


def good_with(*present: str) -> Answers:
    answers: Answers = {"overall_rating": "good"}
    for item_id in present:
        answers[item_id] = "present"
    return answers


def form_without_short_labels() -> list[dict[str, Any]]:
    items = copy.deepcopy(FORM_ITEMS)
    for item in items:
        item.pop("short_label", None)
    return items


def pipe_and_good_rating() -> Answers:
    """Answers that make both dry_pipe (on a dry day) and rating_check fire."""
    answers = good_with("bank_type")
    answers["draining_pipes"] = "present"
    return answers


def rule_ids(chosen: list[Followup]) -> list[str]:
    return [c.rule_id for c in chosen]


def test_an_item_missing_from_the_form_is_named_by_its_id_in_plain_words() -> None:
    assert issues_for(good_with("impervious_right"), []) == "impervious right"
    others = [item for item in FORM_ITEMS if item["id"] != "impervious_right"]
    assert (
        issues_for(good_with("bank_type", "impervious_right"), others)
        == "artificial banks and impervious right"
    )


def test_without_a_short_label_the_label_of_the_present_option_is_used() -> None:
    issues = issues_for(good_with("bank_type"), form_without_short_labels())
    assert issues == "Artificial (concrete or stones with concrete)"


def test_a_blank_or_non_text_short_label_is_ignored() -> None:
    odd_short_labels: tuple[object, ...] = ("   ", "", 7, None)
    for short in odd_short_labels:
        items = form_without_short_labels()
        for item in items:
            if item["id"] == "bank_type":
                item["short_label"] = short
        issues = issues_for(good_with("bank_type"), items)
        assert issues == "Artificial (concrete or stones with concrete)", short


def test_a_short_label_is_trimmed() -> None:
    items = [{"id": "bank_type", "short_label": "  a concrete bank  ", "text": "Bank type"}]
    assert issues_for(good_with("bank_type"), items) == "a concrete bank"


def test_option_lookup_skips_odd_options_and_blank_labels_and_trims_the_one_it_uses() -> None:
    item: dict[str, Any] = {
        "id": "bank_type",
        "text": "Bank type",
        "options": [
            "present",
            {"value": "absent", "label": "Natural"},
            {"value": "present", "label": "   "},
            {"value": "present", "label": 3},
            {"value": "present"},
            {"value": "present", "label": "  Concrete wall  "},
            {"value": "present", "label": "Later option"},
        ],
    }
    assert issues_for(good_with("bank_type"), [item]) == "Concrete wall"


def test_when_no_option_gives_a_label_the_item_text_is_used() -> None:
    no_match: dict[str, Any] = {
        "id": "bank_type",
        "text": "  Bank type  ",
        "options": [{"value": "absent", "label": "Natural"}, {"value": "present", "label": ""}],
    }
    assert issues_for(good_with("bank_type"), [no_match]) == "Bank type"
    empty_options: tuple[object, ...] = (None, [], ())
    for options in empty_options:
        plain: dict[str, Any] = {"id": "sewage_discharge", "text": "Sewage?", "options": options}
        assert issues_for(good_with("sewage_discharge"), [plain]) == "Sewage?"
    real = form_without_short_labels()
    assert (
        issues_for(good_with("impervious_left"), real)
        == "Is more than one third of the left margin covered by impervious areas"
        " (such as roads, sidewalks or buildings)?"
    )


def test_with_no_usable_text_the_item_id_is_used_in_plain_words() -> None:
    odd_texts: tuple[object, ...] = (None, "", "   ", 12)
    for text in odd_texts:
        item: dict[str, Any] = {"id": "invasive_species", "text": text, "short_label": " "}
        assert issues_for(good_with("invasive_species"), [item]) == "invasive species"
    bare = [{"id": "invasive_species"}]
    assert issues_for(good_with("invasive_species"), bare) == "invasive species"


def test_each_issue_takes_its_own_fallback_and_they_keep_the_fixed_order() -> None:
    items: list[dict[str, Any]] = [
        {"id": "sewage_discharge", "text": "Any sewage?"},
        {"id": "invasive_species", "short_label": "invasive plants"},
        {"id": "bank_type", "options": [{"value": "present", "label": "Concrete"}]},
        {"id": "impervious_left"},
    ]
    answers = good_with(
        "sewage_discharge", "invasive_species", "impervious_right", "impervious_left", "bank_type"
    )
    assert issues_for(answers, items) == (
        "Concrete, impervious left, impervious right, invasive plants and Any sewage?"
    )


optional_text = st.none() | st.integers(0, 9) | st.text(max_size=12)
option_shapes = st.fixed_dictionaries(
    {"value": st.sampled_from(["present", "absent", "cant_tell"]), "label": optional_text}
)


@settings(max_examples=150, deadline=None)
@given(
    short=optional_text,
    options=st.none() | st.lists(option_shapes | st.text(max_size=4), max_size=4),
    text=optional_text,
)
def test_the_issue_label_is_never_empty_and_only_ever_comes_from_the_form_item(
    short: object, options: list[object] | None, text: object
) -> None:
    item: dict[str, Any] = {"id": "bank_type", "short_label": short, "options": options}
    item["text"] = text
    label = issues_for(good_with("bank_type"), [item])
    assert label.strip() == label and label
    allowed = {"bank type"}
    for candidate in (short, text):
        if isinstance(candidate, str) and candidate.strip():
            allowed.add(candidate.strip())
    for option in options or []:
        if isinstance(option, dict) and option["value"] == "present":
            if isinstance(option["label"], str) and option["label"].strip():
                allowed.add(option["label"].strip())
    assert label in allowed
    if isinstance(short, str) and short.strip():
        assert label == short.strip()


def test_a_table_without_a_rule_list_asks_nothing() -> None:
    answers = pipe_and_good_rating()
    rules_as_mapping = {r["id"]: r for r in TABLE["rules"]}
    for table in (
        {"max_questions": 2},
        {"max_questions": 2, "rules": None},
        {"max_questions": 2, "rules": "dry_pipe"},
        {"max_questions": 2, "rules": rules_as_mapping},
    ):
        assert select_followups(answers, DRY, None, (), table, form_items=FORM_ITEMS) == []


def test_rules_that_are_not_mappings_or_have_no_text_id_are_skipped() -> None:
    table: dict[str, Any] = {
        "max_questions": 2,
        "rules": [
            "dry_pipe",
            {"priority": 0, "question_key": "followup.no_id"},
            {"id": 5, "priority": 0},
            {"id": None, "priority": 0},
            {"id": "rating_check", "priority": 2, "question_key": "followup.rating_check"},
            {"id": "dry_pipe", "priority": 1, "question_key": "followup.dry_pipe"},
        ],
    }
    answers = pipe_and_good_rating()
    chosen = select_followups(answers, DRY, None, (), table, form_items=FORM_ITEMS)
    assert rule_ids(chosen) == ["dry_pipe", "rating_check"]
    assert [c.question_key for c in chosen] == ["followup.dry_pipe", "followup.rating_check"]


def test_unknown_rule_ids_ahead_in_priority_never_take_a_slot() -> None:
    table: dict[str, Any] = {
        "max_questions": 2,
        "rules": [
            {"id": "ask_the_model", "priority": 0},
            {"id": "free_text", "priority": 0},
            {"id": "dry_pipe", "priority": 5},
            {"id": "rating_check", "priority": 6},
        ],
    }
    answers = pipe_and_good_rating()
    chosen = select_followups(answers, DRY, None, (), table, form_items=FORM_ITEMS)
    assert rule_ids(chosen) == ["dry_pipe", "rating_check"]


def test_rules_with_no_priority_count_as_zero_and_ties_go_by_id() -> None:
    table: dict[str, Any] = {
        "rules": [
            {"id": "rating_check"},
            {"id": "dry_pipe"},
            {"id": "low_score", "priority": 1},
        ],
    }
    answers = pipe_and_good_rating()
    chosen = select_followups(answers, DRY, None, (), table, form_items=FORM_ITEMS)
    assert chosen == [
        Followup(
            rule_id="dry_pipe", kind="yesno", question_key="followup.dry_pipe", params={"days": 3}
        ),
        Followup(
            rule_id="rating_check",
            kind="keep_rating",
            question_key="followup.rating_check",
            params={"issues": "artificial banks", "first_rating": "good"},
        ),
    ]


def test_a_rule_listed_twice_is_asked_once_with_the_higher_priority_wording() -> None:
    table: dict[str, Any] = {
        "max_questions": 2,
        "rules": [
            {"id": "dry_pipe", "priority": 2, "question_key": "followup.dry_pipe_second"},
            {"id": "dry_pipe", "priority": 1, "question_key": "followup.dry_pipe_first"},
        ],
    }
    chosen = select_followups(
        {"draining_pipes": "present"}, DRY, None, (), table, form_items=FORM_ITEMS
    )
    assert chosen == [
        Followup(
            rule_id="dry_pipe",
            kind="yesno",
            question_key="followup.dry_pipe_first",
            params={"days": 3},
        )
    ]
