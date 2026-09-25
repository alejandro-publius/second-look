"""Part 2: whatever the precomputed flags contain, the stored final answer is the person's choice.

The gate fuzz test (core/tests/test_gate.py) shows model output never reaches an answer in the
creek check. This extends it to part 2 (UPDATE_31 section 3): a flag can only make the one
question appear, and never changes an answer by itself.
"""

from __future__ import annotations

import inspect
import json

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from core import assist

ITEMS = [f"a0{i}" for i in range(1, 9)]
json_leaf = st.one_of(
    st.none(), st.booleans(), st.integers(), st.floats(allow_nan=True), st.text(max_size=12)
)
anything = st.recursive(
    json_leaf,
    lambda inner: st.one_of(
        st.lists(inner, max_size=5), st.dictionaries(st.text(max_size=8), inner, max_size=5)
    ),
    max_leaves=25,
)
entry = st.fixed_dictionaries(
    {
        "item_id": st.one_of(st.sampled_from(ITEMS), st.text(max_size=4)),
        "flag": st.one_of(
            st.none(),
            anything,
            st.fixed_dictionaries(
                {
                    "points_to": st.one_of(
                        st.sampled_from(assist.SIDES), st.text(max_size=8), anything
                    )
                }
            ),
        ),
    }
)
flag_docs = st.one_of(anything, st.fixed_dictionaries({"items": st.lists(entry, max_size=10)}))
answers = st.sampled_from(assist.ANSWERS)
person = st.one_of(
    st.just(("keep", None)),
    st.tuples(st.just("change"), answers),
)


@settings(max_examples=600, deadline=None)
@given(
    flags=flag_docs,
    other_flags=flag_docs,
    arm=st.one_of(st.sampled_from(assist.ARMS), st.text(max_size=10)),
    item=st.sampled_from(ITEMS),
    first=answers,
    action=person,
)
def test_fuzz_flags_never_set_or_change_an_answer(
    flags: object,
    other_flags: object,
    arm: str,
    item: str,
    first: str,
    action: tuple[str, str | None],
) -> None:
    def stored(doc: object) -> assist.Settled:
        asked = assist.question_needed(arm, assist.flag_side(doc, item), first)
        if not asked:
            return assist.settle(first, asked=False)
        choice, changed_to = action
        return assist.settle(first, asked=True, choice=choice, changed_to=changed_to)

    got = stored(flags)
    choice, changed_to = action
    if got.question_shown and choice == "change":
        assert got.final_answer == changed_to
    else:
        assert got.final_answer == first
    assert got.first_answer == first
    # Two different flag documents can change whether the question appears, never the answer
    # the person gives for the same actions.
    other = stored(other_flags)
    if other.question_shown == got.question_shown:
        assert other.final_answer == got.final_answer
    if not got.question_shown or choice == "keep":
        assert got.final_answer == first
    # The question never appears outside the assisted arm, whatever the flags say.
    if arm != "assisted":
        assert not got.question_shown


def test_settle_has_no_parameter_for_a_flag() -> None:
    params = set(inspect.signature(assist.settle).parameters)
    assert params == {"first", "asked", "choice", "changed_to"}


def test_question_only_when_a_real_flag_disagrees() -> None:
    assert assist.question_needed("assisted", "present", "no")
    assert assist.question_needed("assisted", "present", "cant_tell")
    assert not assist.question_needed("assisted", "present", "yes")
    assert not assist.question_needed("assisted", None, "no")
    assert not assist.question_needed("unassisted", "present", "no")
    assert not assist.question_needed("assisted", "maybe", "no")


def test_settle_refuses_what_the_person_did_not_do() -> None:
    with pytest.raises(assist.AssistError):
        assist.settle("yes", asked=False, choice="change", changed_to="no")
    with pytest.raises(assist.AssistError):
        assist.settle("yes", asked=True, choice="keep", changed_to="no")
    with pytest.raises(assist.AssistError):
        assist.settle("yes", asked=True, choice="change", changed_to="maybe")
    with pytest.raises(assist.AssistError):
        assist.settle("yes", asked=True)
    with pytest.raises(assist.AssistError):
        assist.settle("perhaps", asked=False)


def test_the_committed_flags_read_as_sides() -> None:
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "results" / "assist_flags.json"
    if not path.exists():
        pytest.skip("results/assist_flags.json is written after the paid run")
    doc = json.loads(path.read_text(encoding="utf-8"))
    for e in doc["items"]:
        side = assist.flag_side(doc, e["item_id"])
        assert side == (e["flag"]["points_to"] if e["flag"] else None)
