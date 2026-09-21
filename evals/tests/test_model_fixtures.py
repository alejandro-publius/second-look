"""Adversarial frames: never under photos/, and a strong fake model ends in cant_tell on them."""

from __future__ import annotations

import hashlib
import io
from pathlib import Path

from PIL import Image

from core.checker import check_photo, force_answer
from core.records import FEATURES
from evals import fixtures
from evals.ablation import CONDITIONS, ContextStub, RuleStub, adversarial_check, frame_is_blank
from evals.fixtures import FIXTURE_NAMES, adversarial_frames
from evals.model_sweep import FakeClient, FakeProfile, load_questions

ROOT = Path(__file__).resolve().parents[2]
MODEL = "claude-opus-5"


def strong_client() -> FakeClient:
    return FakeClient(
        seed=20260920,
        profiles={MODEL: FakeProfile(accuracy=dict.fromkeys(FEATURES, 1.0), malformed_rate=0.0)},
    )


def test_four_frames_are_jpeg_images_of_the_expected_size() -> None:
    frames = adversarial_frames()
    assert tuple(frames) == FIXTURE_NAMES
    for data in frames.values():
        with Image.open(io.BytesIO(data)) as img:
            assert img.format == "JPEG"
            assert img.size == (fixtures.WIDTH, fixtures.HEIGHT)


def test_frames_are_generated_not_committed_and_never_under_photos() -> None:
    fixture_dir = Path(fixtures.__file__).parent
    binaries = [p for p in fixture_dir.rglob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png"}]
    assert binaries == []
    digests = {hashlib.sha256(d).hexdigest() for d in adversarial_frames().values()}
    for img in (ROOT / "photos").rglob("*"):
        if img.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
            assert hashlib.sha256(img.read_bytes()).hexdigest() not in digests


def test_strong_fake_model_says_cant_tell_on_every_frame() -> None:
    client = strong_client()
    for name, data in adversarial_frames().items():
        for feature, question in load_questions().items():
            raw = client.answer(data, question, MODEL)
            assert force_answer(raw.payload).answer == "cant_tell", f"{name} / {feature}"


def test_checker_gives_no_flag_on_any_frame_even_with_every_feature_passed() -> None:
    table = {
        "real": True,
        "models": {MODEL: {f: {"passed": True, "runs": [[True] * 4] * 3} for f in FEATURES}},
    }
    client = strong_client()
    for data in adversarial_frames().values():
        for feature in FEATURES:
            flags = check_photo(
                data, feature, client=client, model_id=MODEL, pass_table=table, enabled=True
            )
            assert flags == []


def test_blank_frames_are_caught_by_the_rule_and_drawn_scenes_are_not() -> None:
    frames = adversarial_frames()
    assert frame_is_blank(frames["blank_white"])
    assert frame_is_blank(frames["blank_black"])
    assert not frame_is_blank(frames["indoor_scene"])
    assert not frame_is_blank(frames["text_screenshot"])


def test_every_ablation_condition_ends_in_no_flag_or_cant_tell_on_the_frames() -> None:
    out = adversarial_check(
        questions=load_questions(),
        rules=RuleStub(seed=1, accuracy=dict.fromkeys(FEATURES, 1.0)),
        context=ContextStub(seed=1, accuracy=1.0),
        vision=strong_client(),
        model_id=MODEL,
    )
    assert set(out) == set(FIXTURE_NAMES)
    for frame, per_feature in out.items():
        for feature, per_cond in per_feature.items():
            assert set(per_cond) == set(CONDITIONS)
            for cond, answer in per_cond.items():
                assert answer in ("no", "cant_tell"), f"{frame}/{feature}/{cond} said {answer}"
