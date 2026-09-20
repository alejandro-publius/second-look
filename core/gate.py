"""The gate between a model and the record (hard rules 2 and 4).

Model output enters this module as an untyped object and leaves it as a list of Flag objects or
as a list of plain-word drop reasons. Nothing else comes out. A Flag can do exactly one thing: make
one follow-up question eligible in core.followups. It never sets an answer or a label.

build_record is the only way a VisitRecord is made. It takes human inputs only. None of its
parameters can carry model output: there is no parameter for flags, for raw model text or for a
model id, and the answers mapping is copied value by value into the record. Any change to this
module ships with a test in core/tests/test_gate.py in the same commit.

Pure. No file or network I/O.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from pydantic import Field, ValidationError, field_validator

from core.records import FEATURES, CheckResult, FeatureId, Frozen, Observer, Spot, VisitRecord

NOTE_MAX_CHARS = 160
REGION_LENGTH = 4
MAX_CANDIDATES = 50
_FLAGS_KEY = "flags"


class Flag(Frozen):
    """One thing a model noticed about one feature. Shown only as "the checker noticed ..."."""

    feature: FeatureId
    confidence: float = Field(ge=0.0, le=1.0)
    note: str = Field(min_length=1, max_length=NOTE_MAX_CHARS)
    region: tuple[float, float, float, float] | None = None

    @field_validator("confidence")
    @classmethod
    def _finite_confidence(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("confidence must be a finite number")
        return value

    @field_validator("region")
    @classmethod
    def _region_fractions(
        cls, value: tuple[float, float, float, float] | None
    ) -> tuple[float, float, float, float] | None:
        if value is None:
            return None
        for part in value:
            if not math.isfinite(part) or part < 0.0 or part > 1.0:
                raise ValueError("region parts must be fractions between 0 and 1")
        return value


def _candidates(raw: object) -> tuple[list[object], list[str]]:
    """Turn any raw model output into a list of candidate objects, or explain why it cannot be."""
    if isinstance(raw, bytes | bytearray):
        try:
            raw = bytes(raw).decode("utf-8")
        except UnicodeDecodeError:
            return [], ["not parseable: bytes are not UTF-8 text"]
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (ValueError, RecursionError):
            return [], ["not parseable: text is not JSON"]
    if isinstance(raw, Mapping):
        inner = raw.get(_FLAGS_KEY)
        if isinstance(inner, list | tuple):
            return list(inner), []
        return [raw], []
    if isinstance(raw, list | tuple):
        return list(raw), []
    return [], [f"not parseable: got {type(raw).__name__}, expected an object or a list"]


def _passed_features(pass_table: object, model_id: object) -> set[str] | None:
    """Features the model passed, or None when the model or the table is unknown."""
    if not isinstance(pass_table, Mapping) or not isinstance(model_id, str):
        return None
    models = pass_table.get("models")
    if not isinstance(models, Mapping):
        return None
    row = models.get(model_id)
    if not isinstance(row, Mapping):
        return None
    passed: set[str] = set()
    for feature in FEATURES:
        cell = row.get(feature)
        if isinstance(cell, Mapping) and cell.get("passed") is True:
            passed.add(feature)
    return passed


def _is_number(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _read_note(value: object) -> tuple[str | None, str | None]:
    if not isinstance(value, str):
        return None, "note is not text"
    note = value.strip()
    if not note:
        return None, "note is empty"
    if len(note) > NOTE_MAX_CHARS:
        return None, f"note too long: {len(note)} characters, {NOTE_MAX_CHARS} at most"
    if any(ch.isspace() and ch != " " for ch in note) or any(ord(ch) < 32 for ch in note):
        return None, "note has line breaks or control characters"
    return note, None


def _read_region(value: object) -> tuple[tuple[float, float, float, float] | None, str | None]:
    if value is None:
        return None, None
    if not isinstance(value, list | tuple) or len(value) != REGION_LENGTH:
        return None, "bad region: needs four numbers x, y, w, h"
    parts: list[float] = []
    for part in value:
        if not _is_number(part) or not math.isfinite(float(part)):
            return None, "bad region: parts must be numbers"
        parts.append(float(part))
    if any(p < 0.0 or p > 1.0 for p in parts):
        return None, "bad region: parts must be fractions between 0 and 1"
    return (parts[0], parts[1], parts[2], parts[3]), None


def _one_flag(candidate: object, passed: set[str], model_id: str) -> tuple[Flag | None, str | None]:
    if not isinstance(candidate, Mapping):
        return None, f"not an object: got {type(candidate).__name__}"
    feature = candidate.get("feature")
    if not isinstance(feature, str) or feature not in FEATURES:
        return None, f"unknown feature {feature!r}"
    if feature not in passed:
        return None, f"feature {feature} not passed by model {model_id}"
    confidence = candidate.get("confidence")
    if not _is_number(confidence):
        return None, "bad confidence: not a number"
    confidence_f = float(confidence)  # type: ignore[arg-type]
    if not math.isfinite(confidence_f) or confidence_f < 0.0 or confidence_f > 1.0:
        return None, "bad confidence: must be between 0 and 1"
    note, note_reason = _read_note(candidate.get("note"))
    if note is None:
        return None, note_reason
    region, region_reason = _read_region(candidate.get("region"))
    if region_reason is not None:
        return None, region_reason
    try:
        flag = Flag(feature=feature, confidence=confidence_f, note=note, region=region)
    except ValidationError:
        return None, "not well formed"
    return flag, None


def _parse(raw: object, model_id: object, pass_table: object) -> tuple[list[Flag], list[str]]:
    candidates, reasons = _candidates(raw)
    if len(candidates) > MAX_CANDIDATES:
        return [], [
            f"too many flags: {len(candidates)}, {MAX_CANDIDATES} at most, dropped everything"
        ]
    passed = _passed_features(pass_table, model_id)
    flags: list[Flag] = []
    for index, candidate in enumerate(candidates, start=1):
        if passed is None:
            reasons.append(f"flag {index}: unknown model {model_id!r}")
            continue
        flag, reason = _one_flag(candidate, passed, str(model_id))
        if flag is None:
            reasons.append(f"flag {index}: {reason}")
        else:
            flags.append(flag)
    return flags, reasons


def parse_flags(
    raw: object, *, model_id: str, pass_table: Mapping[str, Any]
) -> tuple[list[Flag], list[str]]:
    """Parse any model output into Flags or drop it.

    Returns (flags for passed features only, drop reasons). Never raises. Anything that is not a
    well formed flag for a feature the model passed is dropped with a reason in plain words.
    """
    try:
        return _parse(raw, model_id, pass_table)
    except Exception as exc:  # the gate fails closed on any surprise
        return [], [f"not parseable: {type(exc).__name__}"]


def _copy_answers(
    answers: Mapping[str, str | float | list[str]],
) -> dict[str, str | float | list[str]]:
    copied: dict[str, str | float | list[str]] = {}
    for key, value in answers.items():
        if isinstance(value, list):
            copied[str(key)] = [str(v) for v in value]
        else:
            copied[str(key)] = value
    return copied


def build_record(
    *,
    visit_id: str,
    spot: Spot,
    observer: Observer,
    answered_at: datetime,
    answers: Mapping[str, str | float | list[str]],
    first_rating: str | None,
    final_rating: str | None,
    checks: Sequence[CheckResult],
    photo_ids: Sequence[str],
) -> VisitRecord:
    """The only way a VisitRecord is made. No parameter carries model output.

    The answers, the ratings and the photo ids are the human's. The checks record which follow-up
    questions ran and what the human answered to them. The observer's scores come from the test
    the human took. There is no way to pass a Flag, a model id or raw model text into this call.
    """
    return VisitRecord(
        visit_id=visit_id,
        spot=spot,
        observer=observer,
        answered_at=answered_at,
        answers=_copy_answers(answers),
        first_rating=first_rating,
        final_rating=final_rating,
        checks=tuple(checks),
        photo_ids=tuple(str(p) for p in photo_ids),
    )
