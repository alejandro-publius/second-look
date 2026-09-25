"""Follow-up questions, chosen by code and never by a model (hard rule 3).

select_followups is a pure function of the human's answers, the site context (rain), the
observer's test scores, the gate's Flags and the priority table from content/followups.yaml.
Two questions at most. No model call. A Flag can only make the checker_flag question eligible,
and only when the creek check has a question for its feature (an item in content/form.yaml).

Pure. No file or network I/O.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal

from core.gate import Flag
from core.records import FEATURES, FeatureId, Frozen, Observer

DEFAULT_MAX_QUESTIONS = 2
LOW_SCORE_MAX_CORRECT = 2
PRESENT = "present"
ABSENT = "absent"
BEST_RATING = "good"
RATING_ITEM = "overall_rating"
PIPE_ITEMS = ("draining_pipes", "sewage_discharge")
RATING_ISSUE_ITEMS = (
    "bank_type",
    "impervious_left",
    "impervious_right",
    "invasive_species",
    "sewage_discharge",
)

FollowupKind = Literal["yesno", "keep_rating", "look_again", "photo"]


class SiteContext(Frozen):
    """What code knows about the spot at the time of the check."""

    rain: Literal["dry", "wet", "unknown"]
    dry_days: int | None = None
    mm_in_window: float | None = None


class Followup(Frozen):
    """One follow-up question the API may ask. The locale string is filled from params."""

    rule_id: str
    kind: FollowupKind
    question_key: str
    params: dict[str, str | int | float]


def _answer(answers: Mapping[str, Any], item_id: str) -> object:
    return answers.get(item_id)


def _item_by_id(form_items: Sequence[Mapping[str, Any]], item_id: str) -> Mapping[str, Any] | None:
    for item in form_items:
        if item.get("id") == item_id:
            return item
    return None


def _issue_label(item: Mapping[str, Any] | None, item_id: str, value: object) -> str:
    """Plain label for something the person reported, from the form item.

    Order: a short_label on the item if the content ever carries one, then the label of the
    option they chose, then the item text. Never model text.
    """
    if item is None:
        return item_id.replace("_", " ")
    short = item.get("short_label")
    if isinstance(short, str) and short.strip():
        return short.strip()
    for option in item.get("options") or ():
        if isinstance(option, Mapping) and option.get("value") == value:
            label = option.get("label")
            if isinstance(label, str) and label.strip():
                return label.strip()
    text = item.get("text")
    if isinstance(text, str) and text.strip():
        return text.strip()
    return item_id.replace("_", " ")


def _joined(parts: Sequence[str]) -> str:
    """A list of one or more as a person says it: "a", "a and b", "a, b and c" (critic round 14
    B04)."""
    *rest, last = parts
    return f"{', '.join(rest)} and {last}" if rest else last


def _feature_plain_name(feature: str) -> str:
    return feature.replace("_", " ")


def _dry_pipe(
    rule: Mapping[str, Any], answers: Mapping[str, Any], site: SiteContext
) -> Followup | None:
    if site.rain != "dry":
        return None
    if site.dry_days is None or site.dry_days < 1:
        return None
    if not any(_answer(answers, item) == PRESENT for item in PIPE_ITEMS):
        return None
    return Followup(
        rule_id="dry_pipe",
        kind="yesno",
        question_key=str(rule.get("question_key", "followup.dry_pipe")),
        params={"days": int(site.dry_days)},
    )


def _rating_check(
    rule: Mapping[str, Any],
    answers: Mapping[str, Any],
    form_items: Sequence[Mapping[str, Any]],
) -> Followup | None:
    if _answer(answers, RATING_ITEM) != BEST_RATING:
        return None
    issues: list[str] = []
    for item_id in RATING_ISSUE_ITEMS:
        value = _answer(answers, item_id)
        if value == PRESENT:
            issues.append(_issue_label(_item_by_id(form_items, item_id), item_id, value))
    if not issues:
        return None
    return Followup(
        rule_id="rating_check",
        kind="keep_rating",
        question_key=str(rule.get("question_key", "followup.rating_check")),
        params={"issues": _joined(issues), "first_rating": BEST_RATING},
    )


def _asked_features(form_items: Sequence[Mapping[str, Any]]) -> set[str]:
    """The features the creek check asks about: each one that a form item names."""
    return {str(item.get("feature")) for item in form_items if item.get("feature") in FEATURES}


def _checker_flag(
    rule: Mapping[str, Any],
    flags: Sequence[Flag],
    checker_enabled: bool,
    form_items: Sequence[Mapping[str, Any]],
) -> Followup | None:
    if not checker_enabled:
        return None
    # A flag on a feature the check has no question for (the dug-out channel today) makes nothing
    # eligible: the person was never asked about it, so there is nothing to look at again
    # (CRITIC_06 H02).
    asked = _asked_features(form_items)
    usable = [f for f in flags if f.feature in asked]
    if not usable:
        return None
    chosen = max(usable, key=lambda f: f.confidence)
    return Followup(
        rule_id="checker_flag",
        kind="look_again",
        question_key=str(rule.get("question_key", "followup.checker_flag")),
        params={"note": chosen.note, "feature": chosen.feature},
    )


def _low_score(
    rule: Mapping[str, Any],
    answers: Mapping[str, Any],
    observer: Observer | None,
    form_items: Sequence[Mapping[str, Any]],
) -> Followup | None:
    if observer is None:
        return None
    best: tuple[int, int, str, FeatureId] | None = None
    for position, item in enumerate(form_items):
        feature = item.get("feature")
        item_id = item.get("id")
        if feature not in FEATURES or not isinstance(item_id, str):
            continue
        if _answer(answers, item_id) != ABSENT:
            continue
        score = observer.score_for(feature)
        if score is None or score.correct > LOW_SCORE_MAX_CORRECT:
            continue
        key = (score.correct, position, item_id, feature)
        if best is None or key < best:
            best = key
    if best is None:
        return None
    correct, _, item_id, feature = best
    return Followup(
        rule_id="low_score",
        kind="photo",
        question_key=str(rule.get("question_key", "followup.low_score")),
        params={
            "feature": _feature_plain_name(feature),
            "feature_id": feature,
            "item_id": item_id,
            "correct": correct,
        },
    )


def _rules_in_priority(table: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    rules = table.get("rules")
    if not isinstance(rules, list):
        return []
    typed = [r for r in rules if isinstance(r, Mapping) and isinstance(r.get("id"), str)]
    return sorted(typed, key=lambda r: (int(r.get("priority", 0)), str(r["id"])))


def select_followups(
    answers: Mapping[str, str | float | list[str]],
    site: SiteContext,
    observer: Observer | None,
    flags: Sequence[Flag],
    table: Mapping[str, Any],
    *,
    form_items: Sequence[Mapping[str, Any]],
    checker_enabled: bool = False,
) -> list[Followup]:
    """Pure. At most table["max_questions"] (2). Priority order from the table. No model call."""
    cap = int(table.get("max_questions", DEFAULT_MAX_QUESTIONS))
    if cap <= 0:
        return []
    chosen: list[Followup] = []
    for rule in _rules_in_priority(table):
        if len(chosen) >= cap:
            break
        rule_id = rule["id"]
        followup: Followup | None
        if rule_id == "dry_pipe":
            followup = _dry_pipe(rule, answers, site)
        elif rule_id == "rating_check":
            followup = _rating_check(rule, answers, form_items)
        elif rule_id == "checker_flag":
            followup = _checker_flag(rule, flags, checker_enabled, form_items)
        elif rule_id == "low_score":
            followup = _low_score(rule, answers, observer, form_items)
        else:
            followup = None
        if followup is not None and all(f.rule_id != followup.rule_id for f in chosen):
            chosen.append(followup)
    return chosen[:cap]
