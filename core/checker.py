"""The checker that can only ask (master brief section 10, hard rules 2, 4 and 5).

One photo, one feature question, one model answer forced into yes, no or cant_tell plus a note
of at most 160 characters. The answer goes through core.gate.parse_flags and comes back as at
most one Flag, and only for a feature the model passed on the same 16 item test the volunteers
take. The caller shows the note labelled "the checker noticed". This module never writes
anywhere and never pre-fills an answer.

The parser below is shared with evals/model_sweep.py so the test and the checker force model
output the same way.
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from core.records import FEATURES, TestAnswer

if TYPE_CHECKING:
    from core.gate import Flag

log = logging.getLogger(__name__)

NOTE_MAX_CHARS = 160
ANSWERS: tuple[TestAnswer, ...] = ("yes", "no", "cant_tell")
_ROOT = Path(__file__).resolve().parents[1]
_FEATURES_YAML = _ROOT / "content" / "features.yaml"
_WS = re.compile(r"\s+")


class AnswerClient(Protocol):
    """Anything that can answer one question about one photo. The checker only needs this."""

    def answer(self, image_bytes: bytes, question: str, model_id: str) -> Any: ...


@dataclass(frozen=True)
class ForcedAnswer:
    """Model output after forcing. malformed means it was rejected and answer is cant_tell."""

    answer: TestAnswer
    note: str
    malformed: bool
    reason: str


def clean_note(text: object, max_chars: int = NOTE_MAX_CHARS) -> str:
    """Plain text only: no control characters, no angle brackets, one space runs, cut to length."""
    if not isinstance(text, str):
        return ""
    kept = []
    for ch in text:
        if unicodedata.category(ch).startswith("C"):
            kept.append(" ")
        elif ch in "<>":
            continue
        else:
            kept.append(ch)
    flat = _WS.sub(" ", "".join(kept)).strip()
    return flat[:max_chars].rstrip()


def _normalise_answer(value: object) -> TestAnswer | None:
    if not isinstance(value, str):
        return None
    s = value.strip().lower().replace("'", "").replace("-", "_")
    s = _WS.sub("_", s)
    if s == "yes":
        return "yes"
    if s == "no":
        return "no"
    if s in {"cant_tell", "cannot_tell"}:
        return "cant_tell"
    return None


def _as_mapping(payload: object) -> tuple[Mapping[str, Any] | None, str]:
    if isinstance(payload, Mapping):
        return payload, ""
    if isinstance(payload, str):
        text = payload.strip()
        if not text:
            return None, "empty output"
        for candidate in (text, text[text.find("{") : text.rfind("}") + 1]):
            if not candidate:
                continue
            try:
                loaded = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(loaded, Mapping):
                return loaded, ""
            return None, "json is not an object"
        return None, "not json"
    if payload is None:
        return None, "no output"
    return None, f"unexpected type {type(payload).__name__}"


def force_answer(payload: object, *, note_max: int = NOTE_MAX_CHARS) -> ForcedAnswer:
    """Force any model output into yes, no or cant_tell plus a clean note.

    Anything that is not an object with an answer of yes, no or cant_tell becomes cant_tell with
    an empty note and malformed set, so a bad answer can never count as a right one.
    """
    mapping, why = _as_mapping(payload)
    if mapping is None:
        return ForcedAnswer("cant_tell", "", True, why)
    answer = _normalise_answer(mapping.get("answer"))
    if answer is None:
        return ForcedAnswer("cant_tell", "", True, "answer is not yes, no or cant_tell")
    return ForcedAnswer(answer, clean_note(mapping.get("note", ""), note_max), False, "")


def feature_passed(pass_table: Mapping[str, Any], model_id: str, feature: str) -> bool:
    """True only when the committed pass table says this model passed this feature."""
    models = pass_table.get("models")
    if not isinstance(models, Mapping):
        return False
    per_model = models.get(model_id)
    if not isinstance(per_model, Mapping):
        return False
    entry = per_model.get(feature)
    if not isinstance(entry, Mapping):
        return False
    return entry.get("passed") is True


def _questions_from_content(path: Path = _FEATURES_YAML) -> dict[str, str]:
    import yaml

    with path.open(encoding="utf-8") as f:
        doc = yaml.safe_load(f) or {}
    return {
        str(row["id"]): str(row["question"])
        for row in doc.get("features", [])
        if row.get("id") and row.get("question")
    }


def _gate_parse_flags() -> Callable[..., tuple[list[Any], list[str]]] | None:
    """Fetch core.gate.parse_flags at call time. Tests replace this function."""
    try:
        from core.gate import parse_flags
    except ImportError:
        log.warning("core.gate is missing, so the checker drops everything")
        return None
    return parse_flags


def check_photo(
    image_bytes: bytes,
    feature: str,
    *,
    client: AnswerClient,
    model_id: str,
    pass_table: Mapping[str, Any],
    enabled: bool,
    question: str | None = None,
    allow_synthetic: bool = False,
) -> list[Flag]:
    """Ask one feature question about one photo and return at most one gated Flag.

    Returns [] when the checker is off, when the feature is unknown, when the pass table is not
    from a real run (pass_table["real"] is not True; only a test may set allow_synthetic), when
    the model did not pass the feature, when the model did not say yes, when the output is
    malformed, or when the gate drops it. The model is not even asked for a feature it did not
    pass. A synthetic pass table can never license a flag in production.
    """
    if not enabled or feature not in FEATURES:
        return []
    if pass_table.get("real") is not True and not allow_synthetic:
        return []
    if not feature_passed(pass_table, model_id, feature):
        return []
    text = question if question is not None else _questions_from_content().get(feature)
    if not text:
        return []
    raw = client.answer(image_bytes, text, model_id)
    payload = getattr(raw, "payload", raw)
    forced = force_answer(payload)
    if forced.malformed or forced.answer != "yes":
        return []
    candidate = {
        "feature": feature,
        "answer": forced.answer,
        "note": forced.note,
        "confidence": 1.0,
        "model_id": model_id,
    }
    parse_flags = _gate_parse_flags()
    if parse_flags is None:
        return []
    flags, _drops = parse_flags(candidate, model_id=model_id, pass_table=pass_table)
    kept = [
        f
        for f in flags
        if getattr(f, "feature", None) == feature
        and feature_passed(pass_table, model_id, feature)
        and len(getattr(f, "note", "")) <= NOTE_MAX_CHARS
    ]
    return kept[:1]
