"""Health card: approved sentences only, one per audience, stable per seed, else None."""

from __future__ import annotations

from typing import Any

from hypothesis import given, settings
from hypothesis import strategies as st

from core.healthcard import AUDIENCES, HealthCard, pick_actions

SOURCE = "OneAquaHealth indicator factsheet, riparian vegetation"


def sentence(
    sid: str, audience: str, text: str, approved: Any = True, source: Any = SOURCE
) -> dict[str, Any]:
    return {"id": sid, "audience": audience, "text": text, "source": source, "approved": approved}


FULL = [
    sentence("p1", "person", "Wash your hands after touching the water."),
    sentence("p2", "person", "Keep out of the water after heavy rain.", source="Bay Area guidance"),
    sentence("pet1", "pet", "Keep dogs on a lead near outfalls."),
    sentence("c1", "city", "Replant the margins with native trees."),
    sentence("c2", "city", "Fix the sewer connections that run in dry weather."),
    sentence("c3", "city", "Reconnect the floodplain where the channel was dug out."),
]


def test_empty_list_gives_no_card() -> None:
    assert pick_actions([], "seed") is None


def test_nothing_approved_gives_no_card() -> None:
    assert pick_actions([{**s, "approved": False} for s in FULL], "seed") is None


def test_partly_approved_set_gives_no_card() -> None:
    partial = [s if s["audience"] != "city" else {**s, "approved": False} for s in FULL]
    assert pick_actions(partial, "seed") is None
    assert pick_actions([s for s in FULL if s["audience"] != "pet"], "seed") is None


def test_full_set_is_stable_per_seed_and_varies_across_seeds() -> None:
    first = pick_actions(FULL, "spot-1")
    assert first is not None
    assert first == pick_actions(FULL, "spot-1")
    assert pick_actions(list(reversed(FULL)), "spot-1") == first
    cards = {pick_actions(FULL, f"spot-{i}") for i in range(40)}
    assert len(cards) > 1


def test_card_texts_and_sources_line_up() -> None:
    card = pick_actions(FULL, "spot-1")
    assert isinstance(card, HealthCard)
    by_text = {s["text"]: s["source"] for s in FULL}
    assert card.sources == (by_text[card.person], by_text[card.pet], by_text[card.city])
    assert card.pet == "Keep dogs on a lead near outfalls."


def test_unapproved_sentence_never_appears_even_when_it_is_the_only_one() -> None:
    only_pet_unapproved = [s for s in FULL if s["audience"] != "pet"] + [
        sentence("pet-x", "pet", "Let the dog swim.", approved=False)
    ]
    assert pick_actions(only_pet_unapproved, "seed") is None


def test_approved_must_be_exactly_true() -> None:
    for value in ("true", 1, "yes", "approved"):
        loose = [s if s["audience"] != "pet" else {**s, "approved": value} for s in FULL]
        assert pick_actions(loose, "seed") is None


def test_sentence_without_a_source_or_text_is_not_eligible() -> None:
    no_source = [s if s["audience"] != "pet" else {**s, "source": ""} for s in FULL]
    assert pick_actions(no_source, "seed") is None
    no_text = [s if s["audience"] != "pet" else {**s, "text": "   "} for s in FULL]
    assert pick_actions(no_text, "seed") is None


def test_unknown_audience_is_ignored() -> None:
    extra = [*FULL, sentence("w1", "wildlife", "Leave the ducks alone.")]
    assert pick_actions(extra, "seed") == pick_actions(FULL, "seed")


sentences_strategy = st.lists(
    st.fixed_dictionaries(
        {
            "id": st.text(min_size=1, max_size=6),
            "audience": st.sampled_from([*AUDIENCES, "other"]),
            "text": st.text(max_size=30),
            "source": st.text(max_size=10) | st.none(),
            "approved": st.booleans() | st.sampled_from(["true", 1, None]),
        }
    ),
    max_size=12,
)


@settings(max_examples=200, deadline=None)
@given(sentences=sentences_strategy, seed=st.text(max_size=8))
def test_any_card_is_built_only_from_approved_sentences(
    sentences: list[dict[str, Any]], seed: str
) -> None:
    card = pick_actions(sentences, seed)
    approved = {
        (s["audience"], s["text"].strip())
        for s in sentences
        if s["approved"] is True
        and s["text"].strip()
        and isinstance(s["source"], str)
        and s["source"].strip()
    }
    if card is None:
        assert any(all(a != audience for a, _ in approved) for audience in AUDIENCES)
        return
    assert ("person", card.person) in approved
    assert ("pet", card.pet) in approved
    assert ("city", card.city) in approved
    assert card == pick_actions(sentences, seed)
