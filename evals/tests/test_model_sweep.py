"""The sweep: pass rule, parser, fake client, cost log, refusal without a key, batch client."""

from __future__ import annotations

import io
import json
import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from PIL import Image

from core.checker import force_answer
from core.records import FEATURES
from evals import model_sweep as ms
from evals.model_sweep import (
    REFUSAL_NO_KEY,
    CostLog,
    FakeClient,
    FakeProfile,
    Item,
    ModelsConfig,
    ModelSpec,
    Pricing,
    RealClient,
    RealClientRefused,
    Settings,
    feature_passes,
    is_correct,
    item_accuracy,
    pass_table,
    resize_long_side,
    run_sweep,
)

MODEL_IDS = ("claude-haiku-4-5-20251001", "claude-sonnet-5", "claude-opus-5")
T, F = True, False


def jpeg(w: int = 120, h: int = 90, colour: tuple[int, int, int] = (100, 130, 90)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), colour).save(buf, "JPEG")
    return buf.getvalue()


def fake_items() -> list[Item]:
    items = []
    n = 0
    for feature in FEATURES:
        for gold in ("present", "present", "absent", "absent"):
            n += 1
            items.append(
                Item(
                    id=f"t{n:02d}",
                    feature=feature,
                    gold=gold,
                    photo_id=f"p{n:02d}",
                    photo_path=Path("/nowhere") / f"p{n:02d}.jpg",
                    is_placeholder=True,
                )
            )
    return items


QUESTIONS: dict[str, str] = {f: f"Question about {f}?" for f in FEATURES}
IMAGES = {f"t{n:02d}": jpeg(colour=(n * 10 % 255, 90, 90)) for n in range(1, 17)}


def profile(acc: float, malformed: float = 0.0) -> FakeProfile:
    return FakeProfile(accuracy=dict.fromkeys(FEATURES, acc), malformed_rate=malformed)


def sweep(client: FakeClient, models: tuple[str, ...] = ("m",), runs: int = 3) -> list[Any]:
    return run_sweep(
        client, list(models), fake_items(), QUESTIONS, runs=runs, settings=Settings(), images=IMAGES
    )


# pass rule --------------------------------------------------------------------------------------


def test_pass_rule_4_of_4_in_2_of_3_runs_passes() -> None:
    assert feature_passes([[T, T, T, T], [T, T, T, T], [F, T, T, T]])


def test_pass_rule_4_of_4_in_1_of_3_runs_fails() -> None:
    assert not feature_passes([[T, T, T, T], [F, T, T, T], [T, F, T, T]])


def test_pass_rule_3_of_4_in_3_of_3_runs_fails() -> None:
    assert not feature_passes([[T, T, T, F], [T, T, T, F], [T, T, T, F]])


def test_pass_rule_edges() -> None:
    assert feature_passes([[T, T, T, T], [T, T, T, T], [T, T, T, T]])
    assert not feature_passes([[T, T, T], [T, T, T], [T, T, T]]), "a missing item never passes"
    assert not feature_passes([[T, T, T, T]]), "one run is not enough"
    assert not feature_passes([])


def test_planted_passing_and_failing_models() -> None:
    client = FakeClient(
        seed=7, profiles={"strong": profile(1.0), "weak": profile(0.0)}, items=fake_items()
    )
    records = sweep(client, ("strong", "weak"))
    table = pass_table(records, ["strong", "weak"], fake_items(), runs=3, real=False)
    assert all(table["models"]["strong"][f]["passed"] for f in FEATURES)
    assert not any(table["models"]["weak"][f]["passed"] for f in FEATURES)
    assert table["real"] is False and table["synthetic"] is True and table["stamp"] == "SYNTHETIC"
    for f in FEATURES:
        runs = table["models"]["strong"][f]["runs"]
        assert len(runs) == 3 and all(len(r) == 4 for r in runs)
        assert all(isinstance(v, bool) for r in runs for v in r)


def test_item_accuracy_is_a_share_over_runs() -> None:
    client = FakeClient(seed=7, profiles={"strong": profile(1.0)}, items=fake_items())
    acc = item_accuracy(sweep(client, ("strong",)), ["strong"], fake_items(), real=False)
    assert set(acc) >= {"real", "synthetic", "generated_at_utc", "models"}
    assert acc["models"]["strong"] == {i.id: 1.0 for i in fake_items()}


# parser -----------------------------------------------------------------------------------------


@pytest.mark.parametrize("payload", list(ms._MALFORMED_SAMPLES))
def test_every_malformed_sample_is_forced_to_cant_tell(payload: object) -> None:
    forced = force_answer(payload)
    assert forced.malformed
    assert forced.answer == "cant_tell"
    assert forced.note == ""
    assert not is_correct(forced.answer, "present") and not is_correct(forced.answer, "absent")


def test_long_note_is_cut_to_160() -> None:
    forced = force_answer({"answer": "yes", "note": "w" * 500})
    assert not forced.malformed
    assert len(forced.note) == 160


@settings(max_examples=300, deadline=None)
@given(
    st.one_of(
        st.none(),
        st.text(),
        st.binary(),
        st.dictionaries(st.text(), st.one_of(st.text(), st.integers(), st.none())),
        st.lists(st.text()),
    )
)
def test_any_output_is_forced_into_the_three_answers(payload: object) -> None:
    forced = force_answer(payload)
    assert forced.answer in ("yes", "no", "cant_tell")
    assert len(forced.note) <= 160
    assert "\n" not in forced.note and "\x00" not in forced.note
    if forced.malformed:
        assert forced.answer == "cant_tell" and forced.note == ""


# fake client -------------------------------------------------------------------------------------


def test_fake_client_is_deterministic_from_seed_and_item() -> None:
    a = sweep(FakeClient(seed=3, profiles={"m": profile(0.6, 0.1)}, items=fake_items()))
    b = sweep(FakeClient(seed=3, profiles={"m": profile(0.6, 0.1)}, items=fake_items()))
    c = sweep(FakeClient(seed=4, profiles={"m": profile(0.6, 0.1)}, items=fake_items()))
    assert [(r.answer, r.note) for r in a] == [(r.answer, r.note) for r in b]
    assert [r.answer for r in a] != [r.answer for r in c]
    assert any(r.malformed for r in a), "the fake sometimes returns malformed output"


def test_fake_client_answers_cant_tell_for_an_unknown_image() -> None:
    client = FakeClient(seed=1, profiles={"m": profile(1.0)})
    raw = client.answer(jpeg(), "Any question?", "m")
    assert force_answer(raw.payload).answer == "cant_tell"
    assert raw.input_tokens == 0 and raw.output_tokens == 0 and raw.cost_usd == 0.0


def test_resize_long_side_gives_exactly_1092_on_the_long_side() -> None:
    assert ms.image_size(resize_long_side(jpeg(1200, 900))) == (1092, 819)
    assert ms.image_size(resize_long_side(jpeg(900, 1200))) == (819, 1092)
    assert ms.image_size(resize_long_side(jpeg(100, 50))) == (1092, 546)


# cost log ---------------------------------------------------------------------------------------


def test_cost_log_has_one_line_per_fake_call_with_cost_zero(tmp_path: Path) -> None:
    log = CostLog(tmp_path / "cost_log_fake.jsonl")
    client = FakeClient(seed=1, profiles={"m": profile(0.8)}, items=fake_items(), cost_log=log)
    records = sweep(client, ("m",), runs=3)
    lines = [json.loads(s) for s in (tmp_path / "cost_log_fake.jsonl").read_text().splitlines()]
    assert len(lines) == len(records) == 16 * 3
    for line in lines:
        assert set(line) == {
            "ts_utc",
            "model",
            "purpose",
            "input_tokens",
            "output_tokens",
            "cost_usd",
            "real",
        }
        assert line["cost_usd"] == 0.0 and line["real"] is False and line["model"] == "m"


def test_pricing_cost_uses_the_batch_multiplier() -> None:
    pricing = Pricing(
        models={"m": ms.ModelPrice(2.0, 10.0, True)}, batch_multiplier=0.5, batch_checked=True
    )
    assert pricing.cost_usd("m", 1_000_000, 100_000, batch=False) == pytest.approx(3.0)
    assert pricing.cost_usd("m", 1_000_000, 100_000, batch=True) == pytest.approx(1.5)
    assert pricing.cost_usd("unknown", 5, 5, batch=True) == 0.0


# refusal ----------------------------------------------------------------------------------------


def test_real_client_refuses_without_a_key() -> None:
    config = ms.load_models_config()
    with pytest.raises(RealClientRefused, match="ANTHROPIC_API_KEY"):
        RealClient(api_key=None, config=config, pricing=ms.load_pricing())
    with pytest.raises(RealClientRefused):
        RealClient(api_key="", config=config, pricing=ms.load_pricing())


def test_main_real_without_key_prints_one_plain_sentence(tmp_path: Path, capsys: Any) -> None:
    (tmp_path / ".env").write_text("# no key here\nANTHROPIC_API_KEY=\n", encoding="utf-8")
    code = ms.main(
        ["--real", "--env-file", str(tmp_path / ".env"), "--results-dir", str(tmp_path / "r")],
        environ={},
    )
    out = capsys.readouterr().out.strip()
    assert code == 2
    assert out == REFUSAL_NO_KEY
    assert not (tmp_path / "r" / "model_pass_table.json").exists()


def test_env_file_parsing_never_needs_a_real_key(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text('A=1\n# comment\nB="two"\nC=\n', encoding="utf-8")
    assert ms.load_env_file(env) == {"A": "1", "B": "two", "C": ""}
    assert ms.api_key_from(env, {}) is None
    assert ms.api_key_from(tmp_path / "missing.env", {"ANTHROPIC_API_KEY": ""}) is None


def confirmed_config(accepts_temperature: bool = False) -> ModelsConfig:
    base = ms.load_models_config()
    return ModelsConfig(
        models=(ModelSpec("m", "m", True, accepts_temperature),),
        settings=base.settings,
        prompt=base.prompt,
        fake_profiles={},
    )


def checked_pricing() -> Pricing:
    return Pricing(
        models={"m": ms.ModelPrice(2.0, 10.0, True)}, batch_multiplier=0.5, batch_checked=True
    )


def test_real_client_refuses_unconfirmed_model_ids_and_unchecked_prices() -> None:
    sdk = SimpleNamespace()
    base = ms.load_models_config()
    unconfirmed = ModelsConfig(
        models=(ModelSpec("m", "m", False, False),),
        settings=base.settings,
        prompt=base.prompt,
        fake_profiles={},
    )
    client = RealClient(
        api_key="not-a-real-key", config=unconfirmed, pricing=checked_pricing(), sdk_client=sdk
    )
    with pytest.raises(RealClientRefused, match="not yet confirmed"):
        client.check_ready("m")
    unchecked = Pricing(
        models={"m": ms.ModelPrice(2.0, 10.0, False)}, batch_multiplier=0.5, batch_checked=True
    )
    client = RealClient(
        api_key="not-a-real-key",
        config=confirmed_config(),
        pricing=unchecked,
        sdk_client=sdk,
    )
    with pytest.raises(RealClientRefused, match="not yet checked"):
        client.check_ready("m")


# batch client against a stub SDK -----------------------------------------------------------------


def message(payload: object, in_tok: int = 1300, out_tok: int = 40) -> SimpleNamespace:
    block = (
        SimpleNamespace(type="tool_use", name="answer", input=payload)
        if isinstance(payload, dict)
        else SimpleNamespace(type="text", text=str(payload))
    )
    return SimpleNamespace(
        content=[block],
        usage=SimpleNamespace(input_tokens=in_tok, output_tokens=out_tok),
        stop_reason="end_turn",
    )


class StubSDK:
    def __init__(self, fail_id: str | None = None) -> None:
        self.requests: list[dict[str, Any]] = []
        self.polls = 0
        self.fail_id = fail_id
        batches = SimpleNamespace(
            create=self._batch_create, retrieve=self._retrieve, results=self._results
        )
        self.messages = SimpleNamespace(create=self._create, batches=batches)

    def _create(self, **params: Any) -> SimpleNamespace:
        self.requests.append(params)
        return message({"answer": "yes", "note": "single call"})

    def _batch_create(self, *, requests: list[dict[str, Any]]) -> SimpleNamespace:
        self.requests.extend(requests)
        return SimpleNamespace(id="batch_1", processing_status="in_progress")

    def _retrieve(self, batch_id: str) -> SimpleNamespace:
        self.polls += 1
        status = "ended" if self.polls >= 2 else "in_progress"
        return SimpleNamespace(id=batch_id, processing_status=status)

    def _results(self, batch_id: str) -> Any:
        for req in reversed(self.requests):
            cid = req["custom_id"]
            if cid == self.fail_id:
                yield SimpleNamespace(custom_id=cid, result=SimpleNamespace(type="errored"))
            else:
                yield SimpleNamespace(
                    custom_id=cid,
                    result=SimpleNamespace(
                        type="succeeded", message=message({"answer": "no", "note": f"n {cid}"})
                    ),
                )


def test_batch_flow_collects_by_custom_id_and_logs_every_call(tmp_path: Path) -> None:
    sdk = StubSDK(fail_id="q00001")
    log = CostLog(tmp_path / "cost.jsonl")
    client = RealClient(
        api_key="not-a-real-key",
        config=confirmed_config(),
        pricing=checked_pricing(),
        cost_log=log,
        sdk_client=sdk,
        poll_seconds=1.0,
        sleep=lambda s: None,
    )
    items = fake_items()[:3]
    records = run_sweep(client, ["m"], items, QUESTIONS, runs=1, settings=Settings(), images=IMAGES)
    assert [r.custom_id for r in records] == ["m|t01|r0", "m|t02|r0", "m|t03|r0"]
    assert records[0].answer == "no" and records[0].note == "n q00000"
    # The Batch API refuses any custom_id outside [a-zA-Z0-9_-]{1,64}; ours has a | in it.
    assert all(re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", r["custom_id"]) for r in sdk.requests)
    assert records[1].error == "errored" and records[1].answer == "cant_tell"
    assert not records[1].correct
    assert records[0].input_tokens == 1300 and records[0].output_tokens == 40
    assert records[0].cost_usd == pytest.approx((1300 * 2.0 + 40 * 10.0) / 1e6 * 0.5)
    assert sdk.polls == 2
    lines = [json.loads(s) for s in (tmp_path / "cost.jsonl").read_text().splitlines()]
    assert len(lines) == 3 and all(line["real"] is True for line in lines)
    params = sdk.requests[0]["params"]
    assert params["model"] == "m" and "temperature" not in params
    assert params["messages"][0]["content"][0]["type"] == "image"
    assert QUESTIONS["artificial_bank"] in params["messages"][0]["content"][1]["text"]
    assert params["tools"][0]["name"] == "answer"


def test_single_answer_sends_temperature_only_where_accepted() -> None:
    sdk = StubSDK()
    client = RealClient(
        api_key="not-a-real-key",
        config=confirmed_config(accepts_temperature=True),
        pricing=checked_pricing(),
        sdk_client=sdk,
    )
    raw = client.answer(jpeg(), "Q?", "m")
    assert force_answer(raw.payload).answer == "yes"
    assert sdk.requests[0]["temperature"] == 0.0
    assert raw.cost_usd == pytest.approx((1300 * 2.0 + 40 * 10.0) / 1e6)


def test_raw_from_message_falls_back_to_text() -> None:
    raw = ms.raw_from_message(message('{"answer": "cant_tell", "note": "blurry"}'), "m")
    assert force_answer(raw.payload) == force_answer({"answer": "cant_tell", "note": "blurry"})


# the whole script on the placeholders ----------------------------------------------------------


def test_main_fake_writes_the_contract_files(tmp_path: Path, capsys: Any) -> None:
    code = ms.main(["--fake", "--seed", "20260920", "--results-dir", str(tmp_path)])
    assert code == 0
    out = capsys.readouterr().out
    assert "SYNTHETIC" in out and "features passed:" in out
    table = json.loads((tmp_path / "model_pass_table.json").read_text())
    assert table["real"] is False and table["synthetic"] is True
    assert table["stamp"] == "SYNTHETIC"
    assert set(table["models"]) == set(MODEL_IDS)
    for model in MODEL_IDS:
        for f in FEATURES:
            cell = table["models"][model][f]
            assert isinstance(cell["passed"], bool)
            assert len(cell["runs"]) == 3 and all(len(r) == 4 for r in cell["runs"])
    acc = json.loads((tmp_path / "model_item_accuracy.json").read_text())
    assert set(acc) >= {"real", "synthetic", "generated_at_utc", "models"}
    assert acc["real"] is False and acc["synthetic"] is True
    assert all(len(acc["models"][m]) == 16 for m in MODEL_IDS)
    assert all(0.0 <= v <= 1.0 for m in MODEL_IDS for v in acc["models"][m].values())
    sweeps = list(tmp_path.glob("model_sweep_*.json"))
    assert len(sweeps) == 1
    doc = json.loads(sweeps[0].read_text())
    assert len(doc["answers"]) == 3 * 16 * 3 and doc["stamp"] == "SYNTHETIC"
    assert doc["settings"]["resize_long_side_px"] == 1092
    # Real photos come in several shapes, so the sizes differ. What must hold for every one of
    # them is the long side the plan promises: 1092 px.
    sizes = doc["settings"]["image_sizes_sent"]
    assert sizes and all(max(s) == 1092 for s in sizes), sizes
    assert len((tmp_path / "cost_log_fake.jsonl").read_text().splitlines()) == 144


def test_same_seed_same_pass_table(tmp_path: Path) -> None:
    ms.main(["--fake", "--seed", "5", "--results-dir", str(tmp_path / "a")])
    ms.main(["--fake", "--seed", "5", "--results-dir", str(tmp_path / "b")])
    a = json.loads((tmp_path / "a" / "model_pass_table.json").read_text())["models"]
    b = json.loads((tmp_path / "b" / "model_pass_table.json").read_text())["models"]
    assert a == b


def test_models_yaml_holds_the_three_ids_confirmed_and_the_resize_rule() -> None:
    config = ms.load_models_config()
    assert tuple(config.model_ids()) == MODEL_IDS
    # Checked on 2026-09-23 against the models and pricing pages; docs/notes/model_ids.md.
    assert all(m.confirmed_against_models_page for m in config.models)
    assert config.settings.temperature == 0 and config.settings.resize_long_side_px == 1092
    questions = ms.load_questions()
    for f in FEATURES:
        assert questions[f] in config.prompt.user_text(questions[f])
    pricing = ms.load_pricing()
    assert set(pricing.models) == set(MODEL_IDS)
    assert all(p.source_checked for p in pricing.models.values()) and pricing.batch_checked
