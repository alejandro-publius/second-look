"""The footage harness: who agrees with whom, what the gate lets through, and what a label is."""

from __future__ import annotations

import io
import json
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from core.records import FEATURES
from evals import footage
from evals.fixtures import adversarial_frames
from evals.model_sweep import (
    AnswerRecord,
    FakeClient,
    ModelPrice,
    Pricing,
    Query,
    RawAnswer,
    estimate_cost,
    load_models_config,
)


def rec(model: str, frame: str, feature: str, answer: str, **kw: Any) -> AnswerRecord:
    base = AnswerRecord(
        model=model,
        item_id=f"{frame}|{feature}",
        feature=feature,
        gold="",
        run=0,
        custom_id=f"{model}|{frame}|{feature}|r0",
        answer=answer,  # type: ignore[arg-type]
        note="a concrete wall on the left",
        correct=False,
        malformed=False,
        reason="",
        input_tokens=0,
        output_tokens=0,
        cost_usd=0.0,
        error=None,
        raw=None,
    )
    return replace(base, **kw)


def test_the_majority_over_runs_and_a_tie_reads_as_cant_tell() -> None:
    assert footage.majority(["yes", "yes", "no"]) == "yes"
    assert footage.majority(["yes", "no"]) == "cant_tell"
    assert footage.majority([]) == "cant_tell"


def test_a_frame_is_labelled_only_for_the_feature_its_description_supports() -> None:
    manifest = {
        "v01-00010": {
            "role": "benchmark",
            "scene_id": "video-v01",
            "file": "benchmark/v01-00010.jpg",
            "feature": "artificial_bank",
            "gold_label": "present",
        },
        "v02-00004": {
            "role": "benchmark",
            "scene_id": "video-v02",
            "file": "benchmark/v02-00004.jpg",
            "feature": "",
            "gold_label": "",
        },
        "ph-test-01": {"role": "test", "scene_id": "s1", "file": "test/a.jpg"},
    }
    items = footage.frame_items(manifest, root=Path("/nowhere"))
    assert len(items) == 2 * len(FEATURES)
    golds = {i.id: i.gold for i in items}
    assert golds["v01-00010|artificial_bank"] == "present"
    assert golds["v01-00010|pipe_running"] == ""
    assert all(g == "" for k, g in golds.items() if k.startswith("v02"))


def test_agreement_counts_matching_majorities_on_unlabelled_frames_only() -> None:
    f = "artificial_bank"
    records = [
        rec("a", "x1", f, "yes"),
        rec("b", "x1", f, "yes"),
        rec("a", "x2", f, "no"),
        rec("b", "x2", f, "yes"),
        # A labelled frame never counts towards agreement.
        rec("a", "x3", f, "yes", gold="present"),
        rec("b", "x3", f, "no", gold="present"),
    ]
    cell = footage.model_agreement(records, ["a", "b"])[f]
    pair = cell["pairs"]["a vs b"]
    assert cell["frames"] == 2
    assert pair["agree"] == 1 and pair["share"] == 0.5
    assert cell["yes_share"] == {"a": 0.5, "b": 1.0}


def test_a_synthetic_pass_table_lets_no_flag_through_the_gate() -> None:
    records = [rec("m", "x1", "pipe_running", "yes"), rec("m", "x2", "pipe_running", "no")]
    synthetic = {"real": False, "models": {"m": {"pipe_running": {"passed": True}}}}
    out = footage.gate_outcome(records, synthetic)
    assert out["candidates"] == 1 and out["kept"] == 0 and out["dropped"] == 1
    assert out["not_candidates"] == {"answered no, so no flag is proposed": 1}


def test_a_real_table_keeps_a_passed_feature_and_drops_one_that_was_not_passed() -> None:
    records = [rec("m", "x1", "pipe_running", "yes"), rec("m", "x1", "invasive_plant", "yes")]
    table = {
        "real": True,
        "models": {"m": {"pipe_running": {"passed": True}, "invasive_plant": {"passed": False}}},
    }
    out = footage.gate_outcome(records, table)
    assert out["kept"] == 1 and out["dropped"] == 1
    assert list(out["drop_reasons"]) == ["feature invasive_plant not passed by model m"]


def test_a_malformed_answer_is_never_a_candidate() -> None:
    records = [rec("m", "x1", "pipe_running", "cant_tell", malformed=True)]
    out = footage.gate_outcome(records, {"real": True, "models": {}})
    assert out["candidates"] == 0
    assert out["not_candidates"] == {"malformed answer, forced to cant_tell": 1}


# The cap, with the fake client standing in for the paid one. One footage frame, one run.

MANIFEST = {
    "v01-00001": {
        "id": "v01-00001",
        "role": "benchmark",
        "scene_id": "video-v01",
        "file": "benchmark/v01-00001.jpg",
        "feature": "",
        "gold_label": "",
        "coarse_location": "Chile",
    }
}


def small_jpeg() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (64, 48), (90, 120, 80)).save(buf, "JPEG")
    return buf.getvalue()


def fake_pricing(*models: str) -> Pricing:
    price = ModelPrice(input_per_million=500.0, output_per_million=500.0, source_checked=True)
    return Pricing(models=dict.fromkeys(models, price), batch_multiplier=1.0, batch_checked=True)


class ChargingClient:
    """The fake client with a price on every call, so the test can follow the spend."""

    real = True

    def __init__(self, *, per_call: float, per_adversarial_call: float) -> None:
        items = footage.frame_items(MANIFEST, root=Path("/nowhere"))
        self.inner = FakeClient(seed=1, profiles={}, items=items)
        self.per_call = per_call
        self.per_adversarial_call = per_adversarial_call
        self.custom_ids: list[str] = []

    def answer(self, image_bytes: bytes, question: str, model_id: str) -> RawAnswer:
        return self.inner.answer(image_bytes, question, model_id)

    def answer_many(self, queries: Sequence[Query]) -> list[RawAnswer]:
        out: list[RawAnswer] = []
        for q, raw in zip(queries, self.inner.answer_many(queries), strict=True):
            self.custom_ids.append(q.custom_id)
            adv = "|adv-" in q.custom_id
            out.append(replace(raw, cost_usd=self.per_adversarial_call if adv else self.per_call))
        return out


def expected_usd(pricing: Pricing, model: str) -> tuple[float, float]:
    """What footage.py estimates for one model: its footage frames, then its adversarial frames."""
    settings = load_models_config().settings
    items = footage.frame_items(MANIFEST, root=Path("/nowhere"))
    frames = {i.id: small_jpeg() for i in items}
    adv = footage.adversarial_images()
    return (
        estimate_cost([model], frames, pricing, settings, runs=1)["expected_usd"],
        estimate_cost([model], adv, pricing, settings, runs=1)["expected_usd"],
    )


def run_real(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    client: ChargingClient,
    pricing: Pricing,
    cap: float,
    models: Sequence[str],
) -> dict[str, Any]:
    image = small_jpeg()
    monkeypatch.setattr(footage, "load_manifest", lambda: MANIFEST)
    monkeypatch.setattr(footage, "prepared_images", lambda items, _s: {i.id: image for i in items})
    monkeypatch.setattr(footage, "load_pricing", lambda: pricing)
    monkeypatch.setattr(footage, "build_real_client", lambda **_kw: (client, ""))
    argv = ["--real", "--runs", "1", "--models", *models, "--max-usd", str(cap)]
    assert footage.main([*argv, "--results-dir", str(tmp_path)], environ={}) == 0
    doc: dict[str, Any] = json.loads((tmp_path / "footage_latest.json").read_text("utf-8"))
    return doc


def test_a_model_is_skipped_when_its_adversarial_pass_would_pass_the_cap(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    pricing = fake_pricing("m")
    frames_usd, adv_usd = expected_usd(pricing, "m")
    cap = frames_usd + adv_usd / 2
    assert frames_usd < cap, "the footage frames alone fit, so only the adversarial pass bites"
    client = ChargingClient(per_call=0.0, per_adversarial_call=0.0)
    doc = run_real(monkeypatch, tmp_path, client=client, pricing=pricing, cap=cap, models=["m"])
    assert doc["models"] == []
    assert "adversarial frames" in doc["models_skipped_for_cap"]["m"]
    assert client.custom_ids == [], "nothing is paid for a model the cap stops"
    assert doc["adversarial"] == {}


def test_the_adversarial_pass_is_in_the_spend_and_the_cost_per_100_frames(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    client = ChargingClient(per_call=0.01, per_adversarial_call=0.02)
    doc = run_real(
        monkeypatch, tmp_path, client=client, pricing=fake_pricing("m"), cap=1000.0, models=["m"]
    )
    footage_calls = len(FEATURES)  # one frame, one run
    adv_calls = len(adversarial_frames()) * len(FEATURES)
    assert len(client.custom_ids) == footage_calls + adv_calls
    total = footage_calls * 0.01 + adv_calls * 0.02
    assert doc["cost"]["usd"] == pytest.approx(total)
    assert doc["cost"]["adversarial_usd"] == pytest.approx(adv_calls * 0.02)
    assert doc["cost"]["per_100_frames_usd"] == pytest.approx(total * 100)
    assert set(doc["adversarial"]) == set(adversarial_frames())


def test_what_one_model_spent_on_adversarial_frames_counts_before_the_next_model(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    pricing = fake_pricing("a", "b")
    frames_usd, adv_usd = expected_usd(pricing, "a")
    cap = 1.5 * (frames_usd + adv_usd)
    # Model a fits the cap, then its adversarial pass costs the whole cap.
    adv_calls = len(adversarial_frames()) * len(FEATURES)
    client = ChargingClient(per_call=0.0, per_adversarial_call=cap / adv_calls)
    doc = run_real(
        monkeypatch, tmp_path, client=client, pricing=pricing, cap=cap, models=["a", "b"]
    )
    assert doc["models"] == ["a"]
    assert "b" in doc["models_skipped_for_cap"]
    assert not any(cid.startswith("b|") for cid in client.custom_ids)
