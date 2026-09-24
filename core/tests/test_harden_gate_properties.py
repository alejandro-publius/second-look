"""Any model output and any pass table give only licensed, well formed Flags, or plain reasons."""

from __future__ import annotations

import functools
import json
import math
import pickle
import re
import unicodedata
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from core.gate import BIDI_CONTROLS, MAX_CANDIDATES, NOTE_MAX_CHARS, Flag, parse_flags
from core.records import FEATURES

MODEL = "fake-vision-1"
OTHER_MODEL = "other-model"
MODEL_POOL = (MODEL, OTHER_MODEL, "claude-sonnet-5", "")
PASS_TABLE: dict[str, Any] = {
    "real": True,
    "synthetic": False,
    "models": {
        MODEL: {
            "artificial_bank": {"passed": True},
            "dug_out_channel": {"passed": False},
            "invasive_plant": {"passed": True},
            "pipe_running": {"passed": "true"},
        },
        OTHER_MODEL: {"artificial_bank": {"passed": False}},
    },
}
COMMITTED_TABLE = Path(__file__).resolve().parents[2] / "results" / "model_pass_table.json"
FLAG_FIELDS = {"feature", "confidence", "note", "region"}
# Words a model may copy from the form. None of them may ever reach a Flag.
MODEL_KEYS = (
    "feature",
    "confidence",
    "note",
    "region",
    "flags",
    "label",
    "answer",
    "site",
    "sentence",
    "model_id",
    "passed",
    "real",
    "models",
    "rating",
)
EXTRA_KEYS = ("label", "answer", "site", "sentence", "model_id", "passed", "rating", "id")
# Too big for a float. 10**5000 is also too long to print, so it only appears in plain tests.
HUGE_NUMBERS = (10**400, -(10**400), 2**1024)
# Every Unicode Bidi_Control code point (Unicode PropList.txt).
UNICODE_BIDI_CONTROLS = (0x061C, 0x200E, 0x200F, *range(0x202A, 0x202F), *range(0x2066, 0x206A))
REASON_INDEX = re.compile(r"flag (\d+): \S")
PY_SHAPES = ("list", "tuple", "flags")
JSON_SHAPES = ("text", "text_flags", "bytes", "bytearray")


def good(**over: Any) -> dict[str, Any]:
    flag: dict[str, Any] = {
        "feature": "artificial_bank",
        "confidence": 0.8,
        "note": "a straight concrete edge on the left bank",
    }
    flag.update(over)
    return flag


def gate(
    raw: object, model_id: Any = MODEL, table: Any = PASS_TABLE
) -> tuple[list[Flag], list[str]]:
    return parse_flags(raw, model_id=model_id, pass_table=table)


def flood_reason(count: int) -> str:
    return f"too many flags: {count}, {MAX_CANDIDATES} at most, dropped everything"


def wrap(candidates: Sequence[Any], shape: str) -> object:
    """Put the same candidates in each form a model client can hand the gate."""
    items = list(candidates)
    if shape == "list":
        return items
    if shape == "tuple":
        return tuple(items)
    if shape == "flags":
        return {"flags": items, "label": "bad bank", "answer": "present", "site": "spot-1"}
    if shape == "text":
        return json.dumps(items)
    if shape == "text_flags":
        return json.dumps({"flags": items, "sentence": "the bank is fine"})
    if shape == "bytes":
        return json.dumps(items).encode()
    return bytearray(json.dumps(items).encode())


def licence_row(table: object, model_id: object) -> Mapping[Any, Any] | None:
    """The row that lets this model speak, read as rule 4 says: only a real run licenses."""
    if not isinstance(table, Mapping) or table.get("real") is not True:
        return None
    models = table.get("models")
    if not isinstance(model_id, str) or not isinstance(models, Mapping):
        return None
    row = models.get(model_id)
    return row if isinstance(row, Mapping) else None


def licensed(table: object, model_id: object, feature: object) -> bool:
    row = licence_row(table, model_id)
    if row is None or feature not in FEATURES:
        return False
    cell = row.get(feature)
    return isinstance(cell, Mapping) and cell.get("passed") is True


def assert_sound(flags: list[Flag], model_id: object, table: object) -> None:
    """Rule 4 and the Flag shape, checked on every kept flag."""
    for flag in flags:
        assert type(flag) is Flag
        assert isinstance(table, Mapping) and table["real"] is True
        assert isinstance(model_id, str)
        assert flag.feature in FEATURES
        assert table["models"][model_id][flag.feature]["passed"] is True
        assert set(vars(flag)) == FLAG_FIELDS
        assert set(flag.model_dump()) == FLAG_FIELDS
        assert flag.model_extra is None
        assert type(flag.confidence) is float
        assert math.isfinite(flag.confidence) and 0.0 <= flag.confidence <= 1.0
        assert isinstance(flag.note, str)
        assert flag.note == flag.note.strip()
        assert 1 <= len(flag.note) <= NOTE_MAX_CHARS
        assert not any(ch.isspace() and ch != " " for ch in flag.note)
        assert not any(ord(ch) < 32 or ch in "<>" or ch in BIDI_CONTROLS for ch in flag.note)
        if flag.region is not None:
            assert isinstance(flag.region, tuple) and len(flag.region) == 4
            for part in flag.region:
                assert type(part) is float and math.isfinite(part) and 0.0 <= part <= 1.0


def assert_flag_comes_from(flag: Flag, candidate: object) -> None:
    """A kept flag carries the candidate's own values and nothing from any other key."""
    assert isinstance(candidate, Mapping)
    assert flag.feature == candidate["feature"]
    assert flag.confidence == float(candidate["confidence"])
    assert flag.note == candidate["note"].strip()
    region = candidate.get("region")
    assert flag.region == (None if region is None else tuple(float(p) for p in region))


def kept_positions(count: int, reasons: list[str]) -> list[int]:
    """The 1-based positions the reasons do not drop. Fails if a reason is not numbered."""
    dropped: list[int] = []
    for reason in reasons:
        match = REASON_INDEX.match(reason)
        assert match is not None, reason
        dropped.append(int(match.group(1)))
    assert dropped == sorted(set(dropped)), "one reason per dropped candidate, in input order"
    assert all(1 <= index <= count for index in dropped)
    return [index for index in range(1, count + 1) if index not in set(dropped)]


def is_subsequence(small: list[Flag], big: list[Flag]) -> bool:
    remaining = iter(big)
    return all(any(item == other for other in remaining) for item in small)


def serialised(flags: list[Flag], form: str) -> object:
    """Kept flags written back out the way a model would send them."""
    if form == "objects":
        return [flag.model_dump() for flag in flags]
    rows = [flag.model_dump(mode="json") for flag in flags]
    if form == "text":
        return json.dumps({"flags": rows})
    return json.dumps(rows).encode()


@functools.cache
def committed_table() -> dict[str, Any]:
    with COMMITTED_TABLE.open(encoding="utf-8") as f:
        table: dict[str, Any] = json.load(f)
    return table


# Strategies. Candidate lists stay small; the flood tests build big ones by repetition.

json_scalars = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-(2**63), max_value=2**63),
    st.floats(),
    st.text(max_size=24),
)
object_keys = st.sampled_from(MODEL_KEYS) | st.text(max_size=8)
json_like = st.recursive(
    json_scalars,
    lambda children: (
        st.lists(children, max_size=5) | st.dictionaries(object_keys, children, max_size=5)
    ),
    max_leaves=24,
)
json_with_huge = st.recursive(
    json_scalars | st.sampled_from(HUGE_NUMBERS),
    lambda children: (
        st.lists(children, max_size=5) | st.dictionaries(object_keys, children, max_size=5)
    ),
    max_leaves=24,
)
anything = st.recursive(
    json_scalars | st.sampled_from(HUGE_NUMBERS) | st.binary(max_size=16),
    lambda children: (
        st.lists(children, max_size=5)
        | st.lists(children, max_size=4).map(tuple)
        | st.dictionaries(object_keys, children, max_size=5)
    ),
    max_leaves=24,
)

note_text = st.text(
    alphabet=st.characters(min_codepoint=32, max_codepoint=126, exclude_characters="<>")
    | st.characters(categories=("L", "N")),
    min_size=1,
    max_size=NOTE_MAX_CHARS,
).filter(lambda s: s.strip() != "")
padding = st.sampled_from(["", " ", "  ", "\t", "\n", " \r\n "])
notes = st.builds(lambda left, core, right: left + core + right, padding, note_text, padding)
confidences = st.floats(min_value=0.0, max_value=1.0) | st.sampled_from([0, 1])
region_parts = st.floats(min_value=0.0, max_value=1.0) | st.sampled_from([0, 1])
regions = (
    st.none() | st.lists(region_parts, min_size=4, max_size=4) | st.tuples(*[region_parts] * 4)
)
extras = st.dictionaries(st.sampled_from(EXTRA_KEYS), json_like, max_size=4)
well_formed = st.builds(
    lambda extra, core: {**extra, **core},
    extras,
    st.fixed_dictionaries(
        {"feature": st.sampled_from(FEATURES), "confidence": confidences, "note": notes},
        optional={"region": regions},
    ),
)
noisy_flag = st.fixed_dictionaries(
    {
        "feature": st.sampled_from(FEATURES) | st.text(max_size=12) | json_scalars,
        "confidence": st.floats() | st.integers(-2, 2) | st.text(max_size=4) | json_scalars,
        "note": notes | st.text(max_size=NOTE_MAX_CHARS + 20) | json_scalars,
    },
    optional={
        "region": st.lists(st.floats() | st.integers(-1, 2), max_size=5) | json_scalars,
        "label": json_like,
        "answer": json_like,
        "sentence": json_like,
        "site": json_like,
    },
)
json_candidate = st.one_of(well_formed, well_formed, noisy_flag, json_like)
py_candidate = st.one_of(
    json_candidate,
    json_candidate,
    st.binary(max_size=8),
    st.lists(json_like, max_size=3).map(tuple),
)

passed_values = st.sampled_from([True, False, 1, 0, 1.0, "true", "True", None, [True]])
cells = st.one_of(
    st.fixed_dictionaries(
        {"passed": st.just(True) | passed_values},
        optional={"runs": st.lists(st.lists(st.booleans(), max_size=4), max_size=3)},
    ),
    st.dictionaries(
        st.sampled_from(["Passed", "pass", "ok", "passed "]), st.just(True), max_size=2
    ),
    json_scalars,
)
row_keys = st.sampled_from(FEATURES) | st.sampled_from(["litter", "Artificial_bank", "label"])
rows = st.one_of(
    st.dictionaries(row_keys, cells, max_size=6),
    st.lists(st.sampled_from(FEATURES), max_size=4),
    json_scalars,
)
model_keys = st.sampled_from(MODEL_POOL) | st.text(max_size=10)
models_part = st.one_of(
    st.dictionaries(model_keys, rows, max_size=4), st.lists(model_keys, max_size=3), json_scalars
)
reals = st.just(True) | st.sampled_from([False, None, 1, 1.0, "true", "True", [True]])
licensing_tables = st.builds(
    lambda chosen: {
        "real": True,
        "models": {
            model: {feature: {"passed": passed} for feature, passed in row.items()}
            for model, row in chosen.items()
        },
    },
    st.dictionaries(
        st.sampled_from(MODEL_POOL),
        st.dictionaries(st.sampled_from(FEATURES), st.sampled_from([True, True, False])),
        min_size=1,
        max_size=3,
    ),
)
tables = st.one_of(
    st.just(PASS_TABLE),
    licensing_tables,
    licensing_tables,
    st.fixed_dictionaries(
        {"real": reals, "models": models_part},
        optional={"synthetic": st.booleans(), "stamp": st.text(max_size=10), "label": json_like},
    ),
    st.fixed_dictionaries({"models": models_part}),
    json_like,
)


def variants(model_id: str) -> list[str]:
    """Names that are close to a model id but not the same id."""
    return [model_id.upper(), f" {model_id}", f"{model_id} ", model_id[:-1], f"{model_id}-v2"]


@st.composite
def table_and_model(draw: st.DrawFn) -> tuple[Any, Any]:
    """Mostly a table that licenses something and a model it names, so flags get kept."""
    kind = draw(st.sampled_from(["pass_table", "licensing", "licensing", "any"]))
    table = draw(
        {"pass_table": st.just(PASS_TABLE), "licensing": licensing_tables}.get(kind, tables)
    )
    known: list[str] = []
    if isinstance(table, Mapping) and isinstance(table.get("models"), Mapping):
        known = sorted(k for k in table["models"] if isinstance(k, str))
    if known and draw(st.sampled_from([True, True, True, False])):
        return table, draw(st.sampled_from(known))
    options: list[st.SearchStrategy[Any]] = [
        st.sampled_from(MODEL_POOL),
        st.text(max_size=10),
        st.none() | st.integers() | st.binary(max_size=8) | st.lists(st.text(max_size=4)),
    ]
    if known:
        options.append(st.sampled_from(known).flatmap(lambda k: st.sampled_from(variants(k))))
    return table, draw(st.one_of(options))


@st.composite
def shaped_candidates(draw: st.DrawFn) -> tuple[list[Any], object]:
    shape = draw(st.sampled_from(PY_SHAPES + JSON_SHAPES))
    element = py_candidate if shape in PY_SHAPES else json_candidate
    some = draw(st.lists(element, max_size=8))
    candidates = (some * draw(st.integers(1, 5)))[:MAX_CANDIDATES]
    return candidates, wrap(candidates, shape)


raw_anything = st.one_of(
    anything,
    st.lists(py_candidate, max_size=8),
    st.fixed_dictionaries(
        {"flags": st.lists(py_candidate, max_size=8)},
        optional={key: anything for key in ("label", "answer", "site", "sentence")},
    ),
    json_with_huge.map(json.dumps),
    json_with_huge.map(lambda value: json.dumps(value).encode()),
    st.lists(json_candidate, max_size=8).map(json.dumps),
    st.text(max_size=40),
    st.binary(max_size=40),
    st.builds(lambda item, n: [item] * n, py_candidate, st.integers(0, 3 * MAX_CANDIDATES)),
)
tables_any = st.one_of(st.just(PASS_TABLE), tables, anything)
models_any = st.one_of(st.just(MODEL), st.sampled_from(MODEL_POOL), st.text(max_size=12), anything)


# 1. The gate never raises, and it hands back kept flags plus drop reasons.


@settings(max_examples=300, deadline=None, database=None)
@given(raw=raw_anything, model_id=models_any, table=tables_any)
def test_the_gate_never_raises_and_leaves_its_inputs_as_they_were(
    raw: object, model_id: object, table: object
) -> None:
    before = pickle.dumps((raw, model_id, table))
    result = gate(raw, model_id, table)
    assert isinstance(result, tuple) and len(result) == 2
    flags, reasons = result
    assert isinstance(flags, list) and isinstance(reasons, list)
    assert all(isinstance(reason, str) and reason for reason in reasons)
    assert len(flags) <= MAX_CANDIDATES
    assert_sound(flags, model_id, table)
    assert pickle.dumps((raw, model_id, table)) == before


def deep_list(depth: int) -> list[Any]:
    nested: list[Any] = []
    for _ in range(depth):
        nested = [nested]
    return nested


def deep_dict(depth: int) -> dict[str, Any]:
    nested: dict[str, Any] = {}
    for _ in range(depth):
        nested = {"feature": nested, "label": "x"}
    return nested


@pytest.mark.parametrize(
    "raw",
    [
        deep_list(100_000),
        deep_dict(100_000),
        [good(feature=deep_list(100_000))],
        [good(note=deep_dict(100_000))],
        [good(confidence=deep_list(100_000))],
        [good(region=deep_list(100_000))],
        "[" * 100_000 + "]" * 100_000,
        '{"flags": ' * 50_000 + "[]" + "}" * 50_000,
        [good(feature=10**5000)],
        [good(confidence=10**5000)],
        {"flags": [good()] * MAX_CANDIDATES, "label": 10**5000},
    ],
    ids=[
        "deep-list",
        "deep-object",
        "deep-feature",
        "deep-note",
        "deep-confidence",
        "deep-region",
        "deep-json-text",
        "deep-flags-text",
        "feature-too-long-to-print",
        "confidence-too-long-to-print",
        "wrapper-key-too-long-to-print",
    ],
)
def test_hostile_nesting_and_huge_numbers_never_raise(raw: object) -> None:
    flags, reasons = gate(raw)
    assert all(isinstance(reason, str) and reason for reason in reasons)
    assert_sound(flags, MODEL, PASS_TABLE)


# 2. Rule 4: a kept flag names a feature that this exact model passed, with passed exactly true.


@settings(max_examples=200, deadline=None, database=None)
@given(shaped=shaped_candidates(), table_model=table_and_model())
def test_every_kept_flag_is_licensed_for_that_exact_model(
    shaped: tuple[list[Any], object], table_model: tuple[Any, Any]
) -> None:
    _, raw = shaped
    table, model_id = table_model
    flags, _ = gate(raw, model_id, table)
    assert_sound(flags, model_id, table)
    assert all(licensed(table, model_id, flag.feature) for flag in flags)


@settings(max_examples=200, deadline=None, database=None)
@given(candidates=st.lists(well_formed, max_size=10), table_model=table_and_model())
def test_a_well_formed_flag_is_kept_exactly_when_the_table_licenses_it(
    candidates: list[dict[str, Any]], table_model: tuple[Any, Any]
) -> None:
    table, model_id = table_model
    flags, reasons = gate(candidates, model_id, table)
    expected = [c for c in candidates if licensed(table, model_id, c["feature"])]
    assert len(flags) == len(expected)
    for flag, candidate in zip(flags, expected, strict=True):
        assert_flag_comes_from(flag, candidate)
    assert len(reasons) == len(candidates) - len(expected)


BREAKS = ("real", "no_real", "not_a_table", "models", "row", "unknown_model", "near_id", "not_str")


@st.composite
def silenced(draw: st.DrawFn) -> tuple[Any, Any, str]:
    """A table that would license every feature, broken in exactly one way."""
    ids = draw(st.lists(st.sampled_from(MODEL_POOL), min_size=1, max_size=3, unique=True))
    table: Any = {
        "real": True,
        "models": {m: {f: {"passed": True} for f in FEATURES} for m in ids},
    }
    model_id: Any = draw(st.sampled_from(ids))
    how = draw(st.sampled_from(BREAKS))
    if how == "real":
        table["real"] = draw(st.sampled_from([False, None, 1, 1.0, "true", "True", [True]]))
    elif how == "no_real":
        del table["real"]
    elif how == "not_a_table":
        table = draw(
            st.none()
            | st.text(max_size=8)
            | st.integers()
            | st.just(list(table.items()))
            | st.just(json.dumps(table))
        )
    elif how == "models":
        table["models"] = draw(st.just(list(table["models"].items())) | st.just(ids) | json_scalars)
    elif how == "row":
        table["models"][model_id] = draw(st.just(list(FEATURES)) | json_scalars)
    elif how == "unknown_model":
        model_id = draw(st.text(max_size=12).filter(lambda s: s not in ids))
    elif how == "near_id":
        model_id = draw(st.sampled_from([v for v in variants(model_id) if v not in ids]))
    else:
        model_id = draw(
            st.none()
            | st.integers()
            | st.just(model_id.encode())
            | st.just([model_id])
            | st.just((model_id,))
        )
    return table, model_id, how


@settings(max_examples=150, deadline=None, database=None)
@given(candidates=st.lists(well_formed, min_size=1, max_size=8), broken=silenced())
def test_a_table_not_from_a_real_run_a_missing_table_or_an_unknown_model_keeps_nothing(
    candidates: list[dict[str, Any]], broken: tuple[Any, Any, str]
) -> None:
    table, model_id, _ = broken
    flags, reasons = gate(candidates, model_id, table)
    assert flags == []
    assert reasons == [
        f"flag {index}: unknown model {model_id!r}" for index in range(1, len(candidates) + 1)
    ]


@settings(max_examples=100, deadline=None, database=None)
@given(
    passed=json_like.filter(lambda value: value is not True),
    candidate=well_formed,
    cell_extra=st.dictionaries(st.sampled_from(["runs", "label", "Passed"]), st.just(True)),
)
def test_only_passed_exactly_true_licenses_a_feature(
    passed: object, candidate: dict[str, Any], cell_extra: dict[str, Any]
) -> None:
    feature = candidate["feature"]
    table = {"real": True, "models": {MODEL: {feature: {**cell_extra, "passed": passed}}}}
    flags, reasons = gate([candidate], MODEL, table)
    assert flags == []
    assert reasons == [f"flag 1: feature {feature} not passed by model {MODEL}"]


@settings(max_examples=60, deadline=None, database=None)
@given(candidates=st.lists(well_formed, max_size=8), as_if_real=st.booleans(), data=st.data())
def test_the_committed_pass_table_licenses_only_what_it_marks_passed(
    candidates: list[dict[str, Any]], as_if_real: bool, data: st.DataObject
) -> None:
    table = dict(committed_table())
    if as_if_real:
        table["real"] = True  # a copy, to prove the cells are read one by one
    ids = sorted(k for k in table.get("models", {}) if isinstance(k, str))
    model_id = data.draw(st.sampled_from([*ids, MODEL]) | st.text(max_size=8))
    flags, _ = gate(candidates, model_id, table)
    assert_sound(flags, model_id, table)
    expected = [c for c in candidates if licensed(table, model_id, c["feature"])]
    assert [f.feature for f in flags] == [c["feature"] for c in expected]
    if committed_table().get("real") is not True and not as_if_real:
        assert flags == []


# 3. A kept flag is a Flag with the four allowed fields and sound values, nothing else.


def test_the_flag_type_allows_four_fields_and_forbids_the_rest() -> None:
    assert set(Flag.model_fields) == FLAG_FIELDS
    assert Flag.model_config.get("extra") == "forbid"
    assert Flag.model_config.get("frozen") is True


@settings(max_examples=200, deadline=None, database=None)
@given(shaped=shaped_candidates())
def test_extra_keys_never_survive_and_kept_values_are_the_candidates_own(
    shaped: tuple[list[Any], object],
) -> None:
    candidates, raw = shaped
    flags, reasons = gate(raw)
    assert_sound(flags, MODEL, PASS_TABLE)
    for flag in flags:
        for key in EXTRA_KEYS:
            assert not hasattr(flag, key)
    for position, flag in zip(kept_positions(len(candidates), reasons), flags, strict=True):
        assert_flag_comes_from(flag, candidates[position - 1])


def test_a_note_with_any_control_character_is_dropped() -> None:
    controls = [chr(c) for c in (*range(0x20), *range(0x7F, 0xA0))]
    assert all(unicodedata.category(ch) == "Cc" for ch in controls), "the whole Cc category"
    kept = [f"U+{ord(ch):04X}" for ch in controls if gate([good(note=f"edge {ch} here")])[0]]
    assert kept == []


def test_a_note_with_any_unicode_direction_control_is_dropped() -> None:
    kept = [
        f"U+{code:04X}"
        for code in UNICODE_BIDI_CONTROLS
        if gate([good(note=f"concrete {chr(code)}edge")])[0]
    ]
    assert kept == []


# 4. Kept plus dropped accounts for every candidate, and kept flags keep the input order.


@settings(max_examples=200, deadline=None, database=None)
@given(shaped=shaped_candidates(), table_model=table_and_model())
def test_every_candidate_is_kept_or_dropped_once_in_input_order(
    shaped: tuple[list[Any], object], table_model: tuple[Any, Any]
) -> None:
    candidates, raw = shaped
    table, model_id = table_model
    flags, reasons = gate(raw, model_id, table)
    assert len(flags) + len(reasons) == len(candidates)
    positions = kept_positions(len(candidates), reasons)
    assert len(positions) == len(flags)
    for position, flag in zip(positions, flags, strict=True):
        assert_flag_comes_from(flag, candidates[position - 1])


GOOD_TEXT = json.dumps(good())
BIG = "1" + "0" * 400


@pytest.mark.xfail(
    strict=True,
    reason="bug: an integer too big for a float raises inside the gate, so good flags drop too",
)
@pytest.mark.parametrize(
    "raw",
    [
        f'[{GOOD_TEXT}, {{"feature": "invasive_plant", "confidence": {BIG}, "note": "reeds"}}]',
        f'[{GOOD_TEXT}, {{"feature": "invasive_plant", "confidence": 0.5, "note": "reeds",'
        f' "region": [0, 0, 0, {BIG}]}}]',
        [good(), good(feature=10**5000)],
    ],
    ids=["confidence-in-json-text", "region-in-json-text", "feature-too-long-to-print"],
)
def test_a_huge_number_drops_only_its_own_flag(raw: object) -> None:
    flags, reasons = gate(raw)
    assert [f.feature for f in flags] == ["artificial_bank"]
    assert len(reasons) == 1 and reasons[0].startswith("flag 2: ")


# 5. Monotone: fewer candidates never keep more, and gating kept flags again changes nothing.


@settings(max_examples=150, deadline=None, database=None)
@given(shaped=shaped_candidates(), table_model=table_and_model(), data=st.data())
def test_removing_a_candidate_never_adds_a_kept_flag(
    shaped: tuple[list[Any], object], table_model: tuple[Any, Any], data: st.DataObject
) -> None:
    candidates, _ = shaped
    table, model_id = table_model
    if not candidates:
        return
    index = data.draw(st.integers(0, len(candidates) - 1))
    fewer = candidates[:index] + candidates[index + 1 :]
    before, _ = gate(candidates, model_id, table)
    after, _ = gate(fewer, model_id, table)
    assert is_subsequence(after, before)
    assert len(before) - len(after) in (0, 1)


@settings(max_examples=150, deadline=None, database=None)
@given(shaped=shaped_candidates(), table_model=table_and_model())
def test_a_list_is_judged_one_candidate_at_a_time(
    shaped: tuple[list[Any], object], table_model: tuple[Any, Any]
) -> None:
    candidates, raw = shaped
    table, model_id = table_model
    together, _ = gate(raw, model_id, table)
    one_by_one = [flag for c in candidates for flag in gate([c], model_id, table)[0]]
    assert together == one_by_one


@settings(max_examples=150, deadline=None, database=None)
@given(
    shaped=shaped_candidates(),
    table_model=table_and_model(),
    form=st.sampled_from(["objects", "text", "bytes"]),
)
def test_gating_the_kept_flags_again_keeps_the_same_flags(
    shaped: tuple[list[Any], object], table_model: tuple[Any, Any], form: str
) -> None:
    _, raw = shaped
    table, model_id = table_model
    kept, _ = gate(raw, model_id, table)
    again, reasons = gate(serialised(kept, form), model_id, table)
    assert again == kept
    assert reasons == []


def test_the_flood_limit_is_the_one_place_where_fewer_candidates_keep_more() -> None:
    """Monotone holds up to the limit. Above it the flood rule drops everything, by design."""
    flood, _ = gate([good()] * (MAX_CANDIDATES + 1))
    at_limit, _ = gate([good()] * MAX_CANDIDATES)
    assert flood == [] and len(at_limit) == MAX_CANDIDATES


# 6. The flood rule: more candidates than the limit drops everything, at every size.


def test_every_size_just_above_the_limit_drops_everything() -> None:
    for count in range(MAX_CANDIDATES + 1, 4 * MAX_CANDIDATES + 1):
        for shape in PY_SHAPES + JSON_SHAPES:
            assert gate(wrap([good()] * count, shape)) == ([], [flood_reason(count)]), shape


def test_a_flood_of_a_million_drops_everything() -> None:
    assert gate([good()] * 1_000_000) == ([], [flood_reason(1_000_000)])


@settings(max_examples=50, deadline=None, database=None)
@given(
    item=py_candidate,
    count=st.integers(MAX_CANDIDATES + 1, 200_000),
    shape=st.sampled_from(PY_SHAPES),
    model_id=models_any,
    table=tables_any,
)
def test_a_flood_of_any_size_drops_everything_whatever_the_model_or_table(
    item: object, count: int, shape: str, model_id: object, table: object
) -> None:
    assert gate(wrap([item] * count, shape), model_id, table) == ([], [flood_reason(count)])


@settings(max_examples=40, deadline=None, database=None)
@given(
    items=st.lists(json_candidate, min_size=1, max_size=4),
    count=st.integers(MAX_CANDIDATES + 1, 3_000),
    shape=st.sampled_from(JSON_SHAPES),
    table_model=table_and_model(),
)
def test_a_flood_sent_as_json_text_drops_everything(
    items: list[Any], count: int, shape: str, table_model: tuple[Any, Any]
) -> None:
    table, model_id = table_model
    candidates = (items * count)[:count]
    assert gate(wrap(candidates, shape), model_id, table) == ([], [flood_reason(count)])


@settings(max_examples=60, deadline=None, database=None)
@given(
    items=st.lists(py_candidate, min_size=1, max_size=4),
    count=st.integers(0, MAX_CANDIDATES),
    shape=st.sampled_from(PY_SHAPES),
    table_model=table_and_model(),
)
def test_a_list_at_or_below_the_limit_is_never_called_a_flood(
    items: list[Any], count: int, shape: str, table_model: tuple[Any, Any]
) -> None:
    table, model_id = table_model
    _, reasons = gate(wrap((items * count)[:count], shape), model_id, table)
    assert not any("too many flags" in reason for reason in reasons)
