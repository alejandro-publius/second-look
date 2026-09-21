"""The checker can only ask (master brief section 10, hard rules 2, 4 and 5)."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pytest
import yaml
from PIL import Image

from core import checker
from core.checker import check_photo, clean_note, feature_passed, force_answer
from core.records import FEATURES

ROOT = Path(__file__).resolve().parents[2]
MODEL = "claude-opus-5"
FEATURE = "artificial_bank"
YES = {"answer": "yes", "note": "a straight concrete wall along the left bank"}


def photo_bytes(colour: tuple[int, int, int] = (90, 120, 80)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (400, 300), colour).save(buf, "JPEG")
    return buf.getvalue()


def table(*passed: str, real: bool = True, model: str = MODEL) -> dict[str, Any]:
    return {
        "real": real,
        "synthetic": not real,
        "generated_at_utc": "2026-09-20T00:00:00+00:00",
        "models": {
            model: {f: {"passed": f in passed, "runs": [[f in passed] * 4] * 3} for f in FEATURES}
        },
    }


class ScriptedClient:
    """Returns a fixed payload and remembers every question it was asked."""

    real = False

    def __init__(self, payload: object) -> None:
        self.payload = payload
        self.questions: list[str] = []
        self.calls = 0

    def answer(self, image_bytes: bytes, question: str, model_id: str) -> Any:
        self.calls += 1
        self.questions.append(question)
        payload = self.payload

        class Raw:
            pass

        raw = Raw()
        raw.payload = payload  # type: ignore[attr-defined]
        return raw


def ask(client: Any, pass_table: dict[str, Any], **kw: Any) -> list[Any]:
    return check_photo(
        photo_bytes(),
        kw.pop("feature", FEATURE),
        client=client,
        model_id=kw.pop("model_id", MODEL),
        pass_table=pass_table,
        enabled=kw.pop("enabled", True),
        **kw,
    )


def test_disabled_returns_nothing_and_never_asks() -> None:
    client = ScriptedClient(YES)
    assert ask(client, table(FEATURE), enabled=False) == []
    assert client.calls == 0


def test_unpassed_feature_returns_nothing_even_when_the_model_is_confident() -> None:
    client = ScriptedClient({"answer": "yes", "note": "definitely concrete", "confidence": 1.0})
    assert ask(client, table()) == []
    assert client.calls == 0, "a feature the model did not pass is not even asked about"


def test_unknown_model_in_pass_table_returns_nothing() -> None:
    client = ScriptedClient(YES)
    assert ask(client, table(FEATURE), model_id="some-other-model") == []
    assert client.calls == 0


def test_synthetic_pass_table_never_licenses_a_flag_by_default() -> None:
    client = ScriptedClient(YES)
    assert ask(client, table(FEATURE, real=False)) == []
    assert ask(client, {"models": table(FEATURE)["models"]}) == []
    assert ask(client, {"real": "true", "models": table(FEATURE)["models"]}) == []
    assert client.calls == 0


def test_allow_synthetic_is_an_explicit_test_only_switch() -> None:
    pytest.importorskip("core.gate")
    client = ScriptedClient(YES)
    out = ask(client, table(FEATURE, real=False), allow_synthetic=True)
    assert len(out) == 1
    assert client.calls == 1


def test_passed_feature_returns_one_flag_through_the_real_gate() -> None:
    pytest.importorskip("core.gate")
    from core.gate import Flag

    client = ScriptedClient(YES)
    out = ask(client, table(FEATURE))
    assert len(out) == 1
    flag = out[0]
    assert isinstance(flag, Flag)
    assert flag.feature == FEATURE
    assert flag.note == YES["note"]
    assert len(flag.note) <= 160
    assert client.calls == 1


def test_passed_feature_returns_one_flag_with_a_monkeypatched_gate(monkeypatch: Any) -> None:
    from pydantic import BaseModel

    class FakeFlag(BaseModel):
        feature: str
        confidence: float
        note: str

    seen: dict[str, Any] = {}

    def fake_parse(raw: object, *, model_id: str, pass_table: Any) -> tuple[list[Any], list[str]]:
        seen["raw"] = raw
        seen["model_id"] = model_id
        assert isinstance(raw, dict)
        flag = FakeFlag(feature=raw["feature"], confidence=raw["confidence"], note=raw["note"])
        return [flag], []

    monkeypatch.setattr(checker, "_gate_parse_flags", lambda: fake_parse)
    out = ask(ScriptedClient(YES), table(FEATURE))
    assert len(out) == 1
    assert out[0].feature == FEATURE
    assert seen["model_id"] == MODEL
    assert seen["raw"]["answer"] == "yes"
    assert 0.0 <= seen["raw"]["confidence"] <= 1.0


def test_gate_output_for_other_features_is_dropped_and_one_flag_at_most(monkeypatch: Any) -> None:
    from pydantic import BaseModel

    class FakeFlag(BaseModel):
        feature: str
        confidence: float
        note: str

    def greedy(raw: object, *, model_id: str, pass_table: Any) -> tuple[list[Any], list[str]]:
        return [
            FakeFlag(feature="pipe_running", confidence=1.0, note="a pipe"),
            FakeFlag(feature=FEATURE, confidence=1.0, note="wall one"),
            FakeFlag(feature=FEATURE, confidence=1.0, note="wall two"),
        ], []

    monkeypatch.setattr(checker, "_gate_parse_flags", lambda: greedy)
    out = ask(ScriptedClient(YES), table(FEATURE, "pipe_running"))
    assert len(out) == 1
    assert out[0].feature == FEATURE
    assert out[0].note == "wall one"


def test_missing_gate_returns_nothing(monkeypatch: Any) -> None:
    monkeypatch.setattr(checker, "_gate_parse_flags", lambda: None)
    assert ask(ScriptedClient(YES), table(FEATURE)) == []


@pytest.mark.parametrize(
    "payload",
    [
        None,
        "",
        "Yes, I think so.",
        '{"answer": "maybe", "note": "hmm"}',
        '{"answer": "yes"',
        "[1, 2, 3]",
        {"verdict": "yes"},
        {"answer": 1, "note": "x"},
        {"answer": ["yes"], "note": "x"},
        b"yes",
        12.5,
    ],
)
def test_malformed_output_returns_nothing(payload: object) -> None:
    assert ask(ScriptedClient(payload), table(FEATURE)) == []


@pytest.mark.parametrize("answer", ["no", "cant_tell", "can't tell", "NO"])
def test_no_and_cant_tell_return_nothing(answer: str) -> None:
    assert ask(ScriptedClient({"answer": answer, "note": "nothing built"}), table(FEATURE)) == []


def test_yes_with_an_empty_note_returns_nothing() -> None:
    assert ask(ScriptedClient({"answer": "yes", "note": "   \n  "}), table(FEATURE)) == []


def test_long_note_is_cut_to_160_and_flat() -> None:
    long_note = ("built <b>wall</b>\nwith\tsteps " * 40).strip()
    out = ask(ScriptedClient({"answer": "yes", "note": long_note}), table(FEATURE))
    assert len(out) == 1
    note = out[0].note
    assert len(note) <= 160
    assert "\n" not in note and "\t" not in note
    assert "<" not in note and ">" not in note


def test_question_is_the_feature_question_word_for_word() -> None:
    with (ROOT / "content" / "features.yaml").open(encoding="utf-8") as f:
        wanted = {r["id"]: r["question"] for r in yaml.safe_load(f)["features"]}
    client = ScriptedClient(YES)
    ask(client, table(FEATURE))
    assert client.questions == [wanted[FEATURE]]


def test_unknown_feature_returns_nothing() -> None:
    client = ScriptedClient(YES)
    bad_table = {"real": True, "models": {MODEL: {"graffiti": {"passed": True}}}}
    assert ask(client, bad_table, feature="graffiti") == []
    assert client.calls == 0


def test_adversarial_fixtures_return_nothing_with_a_strong_fake_model() -> None:
    from evals.fixtures import adversarial_frames
    from evals.model_sweep import FakeClient, FakeProfile

    strong = FakeProfile(accuracy=dict.fromkeys(FEATURES, 1.0), malformed_rate=0.0)
    client = FakeClient(seed=20260920, profiles={MODEL: strong})
    all_passed = table(*FEATURES)
    for name, data in adversarial_frames().items():
        for feature in FEATURES:
            out = check_photo(
                data, feature, client=client, model_id=MODEL, pass_table=all_passed, enabled=True
            )
            assert out == [], f"{name} produced a flag for {feature}"
    assert client.calls == len(adversarial_frames()) * len(FEATURES)


def test_checker_writes_nothing_in_the_working_directory(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.chdir(tmp_path)
    ask(ScriptedClient(YES), table(FEATURE))
    assert list(tmp_path.iterdir()) == []


def test_feature_passed_reads_only_a_true_passed_field() -> None:
    assert feature_passed(table(FEATURE), MODEL, FEATURE)
    assert not feature_passed(table(), MODEL, FEATURE)
    assert not feature_passed({"models": {MODEL: {FEATURE: {"passed": "true"}}}}, MODEL, FEATURE)
    assert not feature_passed({"models": {MODEL: {FEATURE: {"passed": 1}}}}, MODEL, FEATURE)
    assert not feature_passed({"models": []}, MODEL, FEATURE)
    assert not feature_passed({}, MODEL, FEATURE)


def test_force_answer_and_clean_note_basics() -> None:
    assert force_answer({"answer": "YES ", "note": "x"}).answer == "yes"
    assert force_answer('{"answer": "no", "note": "n"}').answer == "no"
    wrapped = 'text before {"answer": "cant_tell", "note": ""} after'
    assert force_answer(wrapped).answer == "cant_tell"
    bad = force_answer("nonsense")
    assert bad.malformed and bad.answer == "cant_tell" and bad.note == ""
    assert clean_note("a\x00b c   d") == "a b c d"
    assert clean_note(None) == ""
    assert len(clean_note("x" * 1000)) == 160
