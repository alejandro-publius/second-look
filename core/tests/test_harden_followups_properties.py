"""For any input the follow-up selector asks two questions at most, stays pure, flags add one."""

from __future__ import annotations

import ast
import copy
import json
import socket
from datetime import date
from pathlib import Path
from typing import Any, NoReturn

import anthropic
import httpx
import pytest
import yaml
from anthropic.resources.messages import AsyncMessages, Messages
from hypothesis import given, settings
from hypothesis import strategies as st

from core.followups import Followup, SiteContext, select_followups
from core.gate import Flag
from core.records import FEATURES, FeatureId, FeatureScore, Observer

ROOT = Path(__file__).resolve().parents[2]
TABLE: dict[str, Any] = yaml.safe_load((ROOT / "content" / "followups.yaml").read_text("utf-8"))
FORM_ITEMS: list[dict[str, Any]] = yaml.safe_load(
    (ROOT / "content" / "form.yaml").read_text("utf-8")
)["items"]
LOCALE: dict[str, str] = json.loads((ROOT / "content" / "locales" / "en.json").read_text("utf-8"))

CONTENT_RULES: dict[str, dict[str, Any]] = {r["id"]: r for r in TABLE["rules"]}
PRIORITY: dict[str, int] = {r["id"]: int(r["priority"]) for r in TABLE["rules"]}
KNOWN_RULES = ("dry_pipe", "rating_check", "checker_flag", "low_score")
KIND_OF_RULE = {
    "dry_pipe": "yesno",
    "rating_check": "keep_rating",
    "checker_flag": "look_again",
    "low_score": "photo",
}
FORM_IDS = [item["id"] for item in FORM_ITEMS]
# The features the creek check has a question for: a checker flag on any other asks nothing.
ASKED: frozenset[str] = frozenset(
    item["feature"] for item in FORM_ITEMS if item.get("feature") in FEATURES
)
TESTED_ON = date(2026, 9, 21)
WET = SiteContext(rain="wet", dry_days=0, mm_in_window=12.0)
BIG_CAP = 10
Answers = dict[str, str | float | list[str]]

SETTINGS = settings(max_examples=200, deadline=None, database=None)


def run(
    answers: Answers,
    site: SiteContext,
    obs: Observer | None,
    flags: list[Flag] | tuple[Flag, ...],
    *,
    table: dict[str, Any] = TABLE,
    enabled: bool = False,
) -> list[Followup]:
    return select_followups(
        answers, site, obs, flags, table, form_items=FORM_ITEMS, checker_enabled=enabled
    )


def with_cap(cap: int) -> dict[str, Any]:
    table = copy.deepcopy(TABLE)
    table["max_questions"] = cap
    return table


def rule_ids(chosen: list[Followup]) -> list[str]:
    return [c.rule_id for c in chosen]


def not_checker(chosen: list[Followup]) -> list[Followup]:
    return [c for c in chosen if c.rule_id != "checker_flag"]


def merge_answers(odd: Answers, known: Answers, focus: Answers) -> Answers:
    return {**odd, **known, **focus}


def make_observer(scores: list[FeatureScore]) -> Observer:
    return Observer(contributor_token="ct-harden-props-01", scores=tuple(scores))


def every_feature(correct: int) -> Observer:
    return make_observer(
        [FeatureScore(feature=f, correct=correct, tested_on=TESTED_ON) for f in FEATURES]
    )


def stray_flag(feature: str, confidence: float, note: str) -> Flag:
    """A Flag for a feature that does not exist, built past validation as if no gate ran."""
    return Flag.model_construct(feature=feature, confidence=confidence, note=note)


RULE_VALUES = ["present", "absent", "cant_tell", "good", "moderate", "poor"]
ODD_VALUES = ["PRESENT", " present", "Present", "Good", "", "yes", "none"]
answer_values = st.one_of(
    st.sampled_from(RULE_VALUES),
    st.one_of(
        st.sampled_from(ODD_VALUES),
        st.text(max_size=8),
        st.floats(),
        st.integers(-3, 3),
        st.lists(st.sampled_from(RULE_VALUES + ODD_VALUES), max_size=3),
    ),
)
odd_keys = st.one_of(
    st.sampled_from(["not_an_item", "", "Draining_Pipes", "draining_pipes ", "overall"]),
    st.text(max_size=10),
)
presence = st.sampled_from(["present", "present", "absent", "absent", "cant_tell"])
RULE_ITEMS = (
    "draining_pipes",
    "sewage_discharge",
    "bank_type",
    "invasive_species",
    "impervious_left",
    "impervious_right",
)
focus_items = {item_id: presence for item_id in RULE_ITEMS}
focus_items["overall_rating"] = st.sampled_from(["good", "good", "moderate", "poor"])
firing_items = {
    "draining_pipes": st.sampled_from(["present", "present", "absent"]),
    "overall_rating": st.just("good"),
    "impervious_left": st.sampled_from(["present", "present", "absent"]),
    "invasive_species": st.sampled_from(["absent", "absent", "present"]),
    "bank_type": presence,
}
odd_answers = st.dictionaries(odd_keys, answer_values, max_size=4)
known_answers = st.dictionaries(st.sampled_from(FORM_IDS), answer_values, max_size=12)
answer_sets = st.one_of(
    st.builds(
        merge_answers, odd_answers, known_answers, st.fixed_dictionaries({}, optional=focus_items)
    ),
    st.builds(merge_answers, odd_answers, known_answers, st.fixed_dictionaries(focus_items)),
    st.builds(merge_answers, odd_answers, known_answers, st.fixed_dictionaries(firing_items)),
)
sites = st.one_of(
    st.builds(
        SiteContext,
        rain=st.sampled_from(["dry", "wet", "unknown"]),
        dry_days=st.none() | st.integers(-2, 5) | st.integers(6, 10_000),
        mm_in_window=st.none() | st.floats(allow_nan=False),
    ),
    st.builds(SiteContext, rain=st.just("dry"), dry_days=st.integers(1, 30)),
)
feature_scores = st.builds(
    FeatureScore,
    feature=st.sampled_from(FEATURES),
    correct=st.integers(0, 4),
    tested_on=st.just(TESTED_ON),
)
observers = st.one_of(
    st.none(),
    st.just(make_observer([])),
    st.integers(0, 4).map(every_feature),
    st.lists(feature_scores, max_size=6).map(make_observer),
)
notes = st.text(min_size=1, max_size=40)
gate_flags = st.builds(
    Flag, feature=st.sampled_from(FEATURES), confidence=st.floats(0, 1), note=notes
)
stray_flags = st.builds(
    stray_flag,
    feature=st.sampled_from(["not_a_feature", "", "Artificial_Bank", "dug out channel"]),
    confidence=st.floats(0, 1),
    note=notes,
)
asked_flags = st.builds(
    Flag, feature=st.sampled_from(sorted(ASKED)), confidence=st.floats(0, 1), note=notes
)
any_flag = gate_flags | stray_flags
flag_lists: st.SearchStrategy[list[Flag]] = st.one_of(
    st.just([]),
    st.lists(any_flag, max_size=4),
    st.lists(any_flag, min_size=1, max_size=5).flatmap(
        lambda pool: st.lists(st.sampled_from(pool), max_size=25)
    ),
)
caps = st.integers(-3, 6)
table_rules = st.lists(
    st.fixed_dictionaries(
        {
            "id": st.sampled_from([*KNOWN_RULES, "ask_the_model", "free_text"]),
            "priority": st.integers(-5, 5),
        }
    ),
    max_size=10,
)
odd_tables = st.builds(
    lambda cap, rules: {"max_questions": cap, "rules": rules},
    caps,
    table_rules,
)


class NetworkRefused(AssertionError):
    """Raised by every patched network or model entry point."""


def refuse(*args: object, **kwargs: object) -> NoReturn:
    raise NetworkRefused("the follow-up selector must not reach the network or a model")


def refuse_network_and_model(mp: pytest.MonkeyPatch) -> None:
    targets: tuple[tuple[object, str], ...] = (
        (httpx.Client, "send"),
        (httpx.AsyncClient, "send"),
        (anthropic.Anthropic, "__init__"),
        (anthropic.AsyncAnthropic, "__init__"),
        (Messages, "create"),
        (AsyncMessages, "create"),
        (socket.socket, "connect"),
        (socket, "create_connection"),
        (socket, "getaddrinfo"),
    )
    for target, name in targets:
        mp.setattr(target, name, refuse)


def imported_modules(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text("utf-8"))):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.add(node.module or "")
    return names


# 1. The cap.


@SETTINGS
@given(answers=answer_sets, site=sites, obs=observers, flags=flag_lists, enabled=st.booleans())
def test_the_content_table_never_asks_more_than_two_questions_for_any_input(
    answers: Answers, site: SiteContext, obs: Observer | None, flags: list[Flag], enabled: bool
) -> None:
    assert TABLE["max_questions"] == 2
    assert len(run(answers, site, obs, flags, enabled=enabled)) <= 2


@SETTINGS
@given(
    answers=answer_sets,
    site=sites,
    obs=observers,
    flags=flag_lists,
    enabled=st.booleans(),
    cap=caps,
)
def test_a_smaller_cap_keeps_the_first_questions_and_a_cap_of_zero_or_less_asks_nothing(
    answers: Answers,
    site: SiteContext,
    obs: Observer | None,
    flags: list[Flag],
    enabled: bool,
    cap: int,
) -> None:
    capped = run(answers, site, obs, flags, table=with_cap(cap), enabled=enabled)
    uncapped = run(answers, site, obs, flags, table=with_cap(BIG_CAP), enabled=enabled)
    assert len(capped) <= max(cap, 0)
    if cap <= 0:
        assert capped == []
    assert capped == uncapped[: max(cap, 0)]


@SETTINGS
@given(
    answers=answer_sets,
    site=sites,
    obs=observers,
    flags=flag_lists,
    enabled=st.booleans(),
    table=odd_tables,
)
def test_any_table_shape_stays_within_its_cap_and_keeps_its_priority_order(
    answers: Answers,
    site: SiteContext,
    obs: Observer | None,
    flags: list[Flag],
    enabled: bool,
    table: dict[str, Any],
) -> None:
    chosen = run(answers, site, obs, flags, table=table, enabled=enabled)
    ids = rule_ids(chosen)
    assert len(chosen) <= max(table["max_questions"], 0)
    assert len(set(ids)) == len(ids)
    assert set(ids) <= set(KNOWN_RULES)
    rank = {
        rule_id: min((r["priority"], r["id"]) for r in table["rules"] if r["id"] == rule_id)
        for rule_id in ids
    }
    assert ids == sorted(ids, key=lambda rule_id: rank[rule_id])


# 2. No duplicates, and only questions the content file defines.


@SETTINGS
@given(
    answers=answer_sets,
    site=sites,
    obs=observers,
    flags=flag_lists,
    enabled=st.booleans(),
    cap=st.integers(0, BIG_CAP),
)
def test_every_question_is_a_distinct_rule_that_the_content_file_defines(
    answers: Answers,
    site: SiteContext,
    obs: Observer | None,
    flags: list[Flag],
    enabled: bool,
    cap: int,
) -> None:
    chosen = run(answers, site, obs, flags, table=with_cap(cap), enabled=enabled)
    ids = rule_ids(chosen)
    assert len(set(ids)) == len(ids)
    assert all(chosen.count(c) == 1 for c in chosen)
    for question in chosen:
        rule = CONTENT_RULES[question.rule_id]
        assert question.question_key == rule["question_key"]
        assert question.kind == KIND_OF_RULE[question.rule_id]
        assert question.question_key in LOCALE
        LOCALE[question.question_key].format(**question.params)


# 3. Purity.


@SETTINGS
@given(
    answers=answer_sets,
    site=sites,
    obs=observers,
    flags=flag_lists,
    enabled=st.booleans(),
    cap=caps,
)
def test_the_same_inputs_give_the_same_questions_and_every_input_is_left_untouched(
    answers: Answers,
    site: SiteContext,
    obs: Observer | None,
    flags: list[Flag],
    enabled: bool,
    cap: int,
) -> None:
    table = with_cap(cap)
    form_items = copy.deepcopy(FORM_ITEMS)
    before = copy.deepcopy((answers, site, obs, flags, table, form_items))
    first = select_followups(
        answers, site, obs, flags, table, form_items=form_items, checker_enabled=enabled
    )
    second = select_followups(
        answers, site, obs, tuple(flags), table, form_items=form_items, checker_enabled=enabled
    )
    assert first == second
    assert (answers, site, obs, flags, table, form_items) == before


@SETTINGS
@given(
    data=st.data(),
    answers=answer_sets,
    site=sites,
    obs=observers,
    flags=flag_lists,
    enabled=st.booleans(),
)
def test_flag_order_changes_nothing_unless_the_surest_flags_tie(
    data: st.DataObject,
    answers: Answers,
    site: SiteContext,
    obs: Observer | None,
    flags: list[Flag],
    enabled: bool,
) -> None:
    shuffled = data.draw(st.permutations(flags))
    original = run(answers, site, obs, flags, enabled=enabled)
    reordered = run(answers, site, obs, shuffled, enabled=enabled)
    assert rule_ids(original) == rule_ids(reordered)
    assert not_checker(original) == not_checker(reordered)
    usable = [f for f in flags if f.feature in ASKED]
    if not usable:
        assert "checker_flag" not in rule_ids(original) + rule_ids(reordered)
        return
    top = max(f.confidence for f in usable)
    surest = {(f.note, f.feature) for f in usable if f.confidence == top}
    for chosen in (original, reordered):
        for question in chosen:
            if question.rule_id == "checker_flag":
                assert (question.params["note"], question.params["feature"]) in surest
    if len(surest) == 1:
        assert original == reordered


@pytest.mark.xfail(
    strict=True,
    reason="bug: on a confidence tie max() keeps the first flag, so list order picks the note",
)
def test_two_flags_with_the_same_confidence_give_the_same_question_in_either_order() -> None:
    bank = Flag(feature="artificial_bank", confidence=0.8, note="a built edge on the left bank")
    reed = Flag(feature="invasive_plant", confidence=0.8, note="a stand of tall reed")
    forward = run({}, WET, None, [bank, reed], enabled=True)
    backward = run({}, WET, None, [reed, bank], enabled=True)
    assert rule_ids(forward) == rule_ids(backward) == ["checker_flag"]
    assert forward == backward


# 4. Flags add at most one checker question.


@SETTINGS
@given(
    answers=answer_sets,
    site=sites,
    obs=observers,
    flags=flag_lists,
    cap=st.integers(0, BIG_CAP),
)
def test_adding_flags_keeps_the_other_questions_in_order_and_adds_one_checker_question_at_most(
    answers: Answers,
    site: SiteContext,
    obs: Observer | None,
    flags: list[Flag],
    cap: int,
) -> None:
    table = with_cap(cap)
    without = run(answers, site, obs, [], table=table, enabled=True)
    flagged = run(answers, site, obs, flags, table=table, enabled=True)
    assert "checker_flag" not in rule_ids(without)
    added = [c for c in flagged if c.rule_id == "checker_flag"]
    assert len(added) <= 1
    rest = not_checker(flagged)
    assert rest == without[: len(rest)]
    pushed_out = without[len(rest) :]
    assert len(pushed_out) <= 1
    if pushed_out:
        # The checker takes one of the two slots (MASTER_BRIEF section 10), so the only
        # question it can push out is one the table ranks below it, and only when the cap is full.
        assert added and len(flagged) == cap
        assert PRIORITY[pushed_out[0].rule_id] > PRIORITY["checker_flag"]
    ranked_above = [c for c in without if PRIORITY[c.rule_id] < PRIORITY["checker_flag"]]
    assert all(c in flagged for c in ranked_above)


@SETTINGS
@given(answers=answer_sets, site=sites, obs=observers, flags=flag_lists, cap=caps)
def test_with_the_checker_ranked_last_adding_flags_never_removes_a_question(
    answers: Answers, site: SiteContext, obs: Observer | None, flags: list[Flag], cap: int
) -> None:
    table = with_cap(cap)
    for rule in table["rules"]:
        if rule["id"] == "checker_flag":
            rule["priority"] = 99
    without = run(answers, site, obs, [], table=table, enabled=True)
    flagged = run(answers, site, obs, flags, table=table, enabled=True)
    assert not_checker(flagged) == without
    assert len(flagged) - len(without) in (0, 1)


@SETTINGS
@given(
    answers=answer_sets,
    site=sites,
    obs=observers,
    asked=asked_flags,
    rest=st.lists(any_flag, max_size=3),
    more=flag_lists,
    cap=caps,
)
def test_once_there_is_a_flag_more_flags_can_only_change_the_checker_note(
    answers: Answers,
    site: SiteContext,
    obs: Observer | None,
    asked: Flag,
    rest: list[Flag],
    more: list[Flag],
    cap: int,
) -> None:
    # "A flag" here is one on a feature the check asks about; any other makes nothing eligible.
    first = [*rest, asked]
    table = with_cap(cap)
    some = run(answers, site, obs, first, table=table, enabled=True)
    many = run(answers, site, obs, first + more, table=table, enabled=True)
    assert rule_ids(some) == rule_ids(many)
    assert not_checker(some) == not_checker(many)


# 5. With the checker off, flags make no difference.


@SETTINGS
@given(
    answers=answer_sets,
    site=sites,
    obs=observers,
    flags=flag_lists,
    table=odd_tables | caps.map(with_cap),
)
def test_with_the_checker_disabled_flags_make_no_difference_at_all(
    answers: Answers,
    site: SiteContext,
    obs: Observer | None,
    flags: list[Flag],
    table: dict[str, Any],
) -> None:
    off = run(answers, site, obs, flags, table=table, enabled=False)
    assert off == run(answers, site, obs, [], table=table, enabled=False)
    assert off == select_followups(answers, site, obs, flags, table, form_items=FORM_ITEMS)
    assert "checker_flag" not in rule_ids(off)


# 6. No network and no model.


def test_the_network_patch_really_refuses_http_and_model_calls() -> None:
    with pytest.MonkeyPatch.context() as mp:
        refuse_network_and_model(mp)
        with pytest.raises(NetworkRefused):
            httpx.Client().get("https://example.invalid/")
        with pytest.raises(NetworkRefused):
            anthropic.Anthropic(api_key="not-a-real-key")
        with pytest.raises(NetworkRefused):
            socket.create_connection(("example.invalid", 443))


@SETTINGS
@given(
    answers=answer_sets,
    site=sites,
    obs=observers,
    flags=flag_lists,
    enabled=st.booleans(),
    cap=caps,
)
def test_the_selector_runs_with_http_and_the_model_client_patched_to_raise(
    answers: Answers,
    site: SiteContext,
    obs: Observer | None,
    flags: list[Flag],
    enabled: bool,
    cap: int,
) -> None:
    table = with_cap(cap)
    expected = run(answers, site, obs, flags, table=table, enabled=enabled)
    with pytest.MonkeyPatch.context() as mp:
        refuse_network_and_model(mp)
        chosen = run(answers, site, obs, flags, table=table, enabled=enabled)
    assert chosen == expected


def test_the_selector_and_what_it_imports_load_no_network_or_model_library() -> None:
    allowed = {"__future__", "collections.abc", "typing", "core.gate", "core.records"}
    assert imported_modules(ROOT / "core" / "followups.py") <= allowed
    forbidden = {"anthropic", "httpx", "requests", "urllib", "http", "socket", "aiohttp"}
    for module in ("gate", "records"):
        roots = {name.split(".")[0] for name in imported_modules(ROOT / "core" / f"{module}.py")}
        assert not roots & forbidden, module


def test_a_flag_for_a_feature_with_no_form_item_asks_nothing() -> None:
    """CRITIC_06 H02: the check has no item for a dug-out channel, so the person was never asked
    about it and a look-again question could change nothing; the flag makes nothing eligible."""
    dug: FeatureId = "dug_out_channel"
    assert dug not in ASKED
    flags = [
        Flag(feature=dug, confidence=0.7, note="a straight dug channel"),
        stray_flag("not_a_feature", 0.9, "something odd"),
    ] * 5
    cases: list[Answers] = [{"draining_pipes": "present"}, {"bank_type": "absent"}]
    for answers in cases:
        chosen = run(answers, WET, every_feature(0), flags, enabled=True)
        assert "checker_flag" not in rule_ids(chosen)
        assert chosen == run(answers, WET, every_feature(0), [], enabled=True)


@SETTINGS
@given(answers=answer_sets, site=sites, obs=observers, flags=flag_lists, cap=caps)
def test_the_checker_question_is_only_ever_about_a_feature_the_check_asks_about(
    answers: Answers, site: SiteContext, obs: Observer | None, flags: list[Flag], cap: int
) -> None:
    chosen = run(answers, site, obs, flags, table=with_cap(cap), enabled=True)
    for question in chosen:
        if question.rule_id == "checker_flag":
            assert question.params["feature"] in ASKED
    unasked = [f for f in flags if f.feature not in ASKED]
    table = with_cap(cap)
    assert run(answers, site, obs, unasked, table=table, enabled=True) == run(
        answers, site, obs, [], table=table, enabled=True
    )
