"""The gate fails closed, the checker drops all without a gate, and bad block ids are refused."""

from __future__ import annotations

import json
import logging
import sys
from collections import Counter
from collections.abc import Iterator, Mapping
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from core import checker, gate
from core.allocator import arm_for_position, arm_names, block_contents
from core.checker import check_photo, feature_passed
from core.gate import Flag, parse_flags
from core.records import FeatureId

MODEL = "fake-vision-1"
FEATURE: FeatureId = "artificial_bank"
SEED = "harden-seed-2026"
QUESTION = "Is the bank built from concrete, stone or metal?"
PASS_TABLE: dict[str, Any] = {
    "real": True,
    "synthetic": False,
    "generated_at_utc": "2026-09-20T00:00:00Z",
    "models": {
        MODEL: {
            "artificial_bank": {"passed": True},
            "dug_out_channel": {"passed": False},
            "invasive_plant": {"passed": True},
            "pipe_running": {"passed": False},
        }
    },
}
YES = {"answer": "yes", "note": "a straight concrete wall along the left bank"}


def good(**over: Any) -> dict[str, Any]:
    flag: dict[str, Any] = {
        "feature": FEATURE,
        "confidence": 0.8,
        "note": "a straight concrete edge on the left bank",
    }
    flag.update(over)
    return flag


class ExplodingMapping(Mapping[str, Any]):
    """Looks like an object, but every lookup raises, like a broken client response."""

    def __getitem__(self, key: str) -> Any:
        raise RuntimeError("lookup failed")

    def __iter__(self) -> Iterator[str]:
        return iter(())

    def __len__(self) -> int:
        return 0


class ExplodingList(list[Any]):
    """Looks like a list, but reading it raises."""

    def __iter__(self) -> Iterator[Any]:
        raise ValueError("iteration failed")


class YesClient:
    """Always says yes and counts how often it was asked."""

    def __init__(self) -> None:
        self.calls = 0

    def answer(self, image_bytes: bytes, question: str, model_id: str) -> Any:
        self.calls += 1
        return YES


# Flag: a confidence that is not a finite number never becomes a Flag.


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_flag_refuses_a_confidence_that_is_not_a_finite_number(value: float) -> None:
    with pytest.raises(ValidationError) as caught:
        Flag(feature=FEATURE, confidence=value, note="x")
    assert [error["loc"] for error in caught.value.errors()] == [("confidence",)]


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_finite_confidence_check_names_the_problem_in_plain_words(value: float) -> None:
    with pytest.raises(ValueError, match="^confidence must be a finite number$"):
        Flag._finite_confidence(value)


@pytest.mark.parametrize("value", [0.0, 0.25, 1.0])
def test_finite_confidence_check_passes_a_finite_number_through_unchanged(value: float) -> None:
    assert Flag._finite_confidence(value) == value


# parse_flags: every kind of input gives flags or plain-word reasons, never an exception.


@pytest.mark.parametrize(
    ("raw", "features", "reasons"),
    [
        (bytearray(json.dumps([good()]).encode()), [FEATURE], []),
        (bytearray(b"\xff\xfe"), [], ["not parseable: bytes are not UTF-8 text"]),
        ((good(), good(feature="invasive_plant")), [FEATURE, "invasive_plant"], []),
        ({"flags": (good(),)}, [FEATURE], []),
        ({"flags": "not a list"}, [], ["flag 1: unknown feature None"]),
        ([], [], []),
        ("[" * 100_000, [], ["not parseable: text is not JSON"]),
        ("42", [], ["not parseable: got int, expected an object or a list"]),
        (json.dumps("just text"), [], ["not parseable: got str, expected an object or a list"]),
    ],
)
def test_parse_flags_handles_each_kind_of_input(
    raw: object, features: list[str], reasons: list[str]
) -> None:
    flags, got_reasons = parse_flags(raw, model_id=MODEL, pass_table=PASS_TABLE)
    assert [f.feature for f in flags] == features
    assert got_reasons == reasons
    assert all(isinstance(f, Flag) for f in flags)


@pytest.mark.parametrize(
    ("raw", "error_name"),
    [
        (ExplodingMapping(), "RuntimeError"),
        (ExplodingList([good()]), "ValueError"),
        ([good(), ExplodingMapping()], "RuntimeError"),
    ],
)
def test_parse_flags_fails_closed_when_the_model_output_raises(
    raw: object, error_name: str
) -> None:
    flags, reasons = parse_flags(raw, model_id=MODEL, pass_table=PASS_TABLE)
    assert flags == []
    assert reasons == [f"not parseable: {error_name}"]


def test_parse_flags_fails_closed_when_the_pass_table_raises() -> None:
    flags, reasons = parse_flags([good()], model_id=MODEL, pass_table=ExplodingMapping())
    assert flags == []
    assert reasons == ["not parseable: RuntimeError"]


def test_a_good_flag_is_dropped_too_when_a_later_candidate_raises() -> None:
    alone, _ = parse_flags([good()], model_id=MODEL, pass_table=PASS_TABLE)
    assert len(alone) == 1
    mixed, reasons = parse_flags(
        [good(), ExplodingMapping()], model_id=MODEL, pass_table=PASS_TABLE
    )
    assert mixed == []
    assert len(reasons) == 1 and reasons[0].startswith("not parseable")


# The checker's lookup of the gate.


def test_checker_looks_up_the_real_gate_parse_flags() -> None:
    assert checker._gate_parse_flags() is gate.parse_flags


def test_checker_gate_lookup_logs_and_returns_none_without_a_gate(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setitem(sys.modules, "core.gate", None)
    with caplog.at_level(logging.WARNING, logger="core.checker"):
        assert checker._gate_parse_flags() is None
    assert [(r.name, r.levelno, r.getMessage()) for r in caplog.records] == [
        ("core.checker", logging.WARNING, "core.gate is missing, so the checker drops everything")
    ]


def test_check_photo_drops_a_yes_when_the_gate_cannot_be_imported(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    client = YesClient()
    kwargs: dict[str, Any] = {
        "client": client,
        "model_id": MODEL,
        "pass_table": PASS_TABLE,
        "enabled": True,
        "question": QUESTION,
    }
    assert len(check_photo(b"photo", FEATURE, **kwargs)) == 1
    monkeypatch.setitem(sys.modules, "core.gate", None)
    with caplog.at_level(logging.WARNING, logger="core.checker"):
        assert check_photo(b"photo", FEATURE, **kwargs) == []
    assert client.calls == 2
    assert "core.gate is missing" in caplog.text


# feature_passed: only an object with passed set to True counts.


@pytest.mark.parametrize(
    "row",
    [
        {FEATURE: True},
        {FEATURE: "passed"},
        {FEATURE: [True]},
        {FEATURE: None},
        {},
        {"invasive_plant": {"passed": True}},
    ],
)
def test_feature_passed_is_false_when_the_entry_for_the_feature_is_not_an_object(
    row: dict[str, Any],
) -> None:
    assert feature_passed({"real": True, "models": {MODEL: row}}, MODEL, FEATURE) is False


def test_check_photo_never_asks_when_the_pass_entry_is_not_an_object() -> None:
    client = YesClient()
    out = check_photo(
        b"photo",
        FEATURE,
        client=client,
        model_id=MODEL,
        pass_table={"real": True, "models": {MODEL: {FEATURE: True}}},
        enabled=True,
        question=QUESTION,
    )
    assert out == []
    assert client.calls == 0


# block_contents: bad arguments are refused with a message that names them.


@pytest.mark.parametrize("block_id", [-1, -5])
def test_block_contents_refuses_a_negative_block_id(block_id: int) -> None:
    with pytest.raises(ValueError, match="^block_id must be 0 or more$"):
        block_contents(SEED, block_id)


def test_negative_position_is_refused_before_it_can_become_a_block_id() -> None:
    with pytest.raises(ValueError, match="^position must be 0 or more$"):
        arm_for_position(SEED, -1)


def test_block_size_is_checked_before_the_block_id() -> None:
    with pytest.raises(ValueError, match="^block must be at least 1$"):
        block_contents(SEED, -1, block=0)


def test_block_zero_is_the_first_block_and_is_allowed() -> None:
    assert Counter(block_contents(SEED, 0)) == {"untrained": 2, "trained": 2}


@pytest.mark.parametrize(
    ("block_id", "extra"),
    [(0, "untrained"), (1, "trained"), (2, "arm_3"), (3, "untrained"), (4, "trained")],
)
def test_spare_slot_rotates_over_the_arms_by_block_id(block_id: int, extra: str) -> None:
    counts = Counter(block_contents(SEED, block_id, k=3, block=4))
    assert counts[extra] == 2
    assert sorted(counts.values()) == [1, 1, 2]


@settings(max_examples=200, deadline=None, database=None, derandomize=True)
@given(
    seed=st.text(max_size=20),
    start=st.integers(min_value=0, max_value=10_000),
    k=st.integers(min_value=2, max_value=5),
    block=st.integers(min_value=1, max_value=12),
)
def test_any_k_consecutive_blocks_are_exactly_balanced(
    seed: str, start: int, k: int, block: int
) -> None:
    names = arm_names(k)
    total: Counter[str] = Counter()
    for block_id in range(start, start + k):
        slots = block_contents(seed, block_id, k=k, block=block)
        assert len(slots) == block
        counts = Counter(slots)
        assert set(counts) <= set(names)
        assert all(counts[n] in (block // k, block // k + 1) for n in names)
        total.update(slots)
    assert {n: total[n] for n in names} == {n: block for n in names}
