"""AI takes the same test as the volunteers (master brief section 8, analysis plan item 8).

For each configured model and each of the 16 test items: resize the photo to 1092 px on the
long side, send the identical feature question, force the answer into yes, no or cant_tell plus
a note cut to 160 characters, three repeat runs. Writes:

- results/model_pass_table.json   a feature passes only if all 4 of its items are right in at
                                  least 2 of 3 runs; core.gate reads models[model][feature].passed
- results/model_item_accuracy.json  accuracy 0 to 1 per model per item over the runs
- results/model_sweep_<stamp>.json  every raw answer and note
- results/cost_log.jsonl          one line per real call (fake runs write cost_log_fake.jsonl)
                                  {ts_utc, model, purpose, input_tokens,
                                  output_tokens, cost_usd, real}; fake calls log cost 0

Run: uv run python evals/model_sweep.py --fake --seed 20260920
     uv run python evals/model_sweep.py --real     (refuses without ANTHROPIC_API_KEY in .env)

The fake client is deterministic from the seed and the item id and never spends anything.
The real client uses the Messages Batch API and refuses to start until the model ids and the
prices are marked as checked in evals/models.yaml and evals/pricing.yaml.
"""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import os
import random
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

import yaml
from PIL import Image

from core.checker import NOTE_MAX_CHARS, ForcedAnswer, force_answer
from core.records import FEATURES, ITEMS_PER_FEATURE, TestAnswer

ROOT = Path(__file__).resolve().parents[1]
MODELS_YAML = ROOT / "evals" / "models.yaml"
PRICING_YAML = ROOT / "evals" / "pricing.yaml"
DEFAULT_RESULTS = ROOT / "results"
DEFAULT_ENV_FILE = ROOT / ".env"
SCRIPT = "evals/model_sweep.py"
DEFAULT_SEED = 20260920
PASS_RUNS_NEEDED = 2
ESTIMATE_OUTPUT_TOKENS = 300
ESTIMATE_TEXT_TOKENS = 200

REFUSAL_NO_KEY = (
    "No ANTHROPIC_API_KEY in .env or the environment, so there is no real model run. "
    "Nothing was sent and nothing was spent."
)
REFUSAL_UNCONFIRMED = (
    "Model id {model} is not yet confirmed against the models page in evals/models.yaml, "
    "so there is no real model run."
)
REFUSAL_UNPRICED = (
    "The price for {model} is not yet checked against the pricing page in evals/pricing.yaml, "
    "so there is no real model run."
)
REFUSAL_OVER_CAP = (
    "The worst case cost of this run is {cost:.2f} USD, above the cap of {cap:.2f} USD, "
    "so there is no real model run."
)

# ---------------------------------------------------------------------------------------------
# Config


@dataclass(frozen=True)
class ModelSpec:
    id: str
    short: str
    confirmed_against_models_page: bool
    accepts_temperature: bool


@dataclass(frozen=True)
class Settings:
    temperature: float = 0.0
    max_tokens: int = 2048
    runs: int = 3
    resize_long_side_px: int = 1092
    image_format: str = "JPEG"
    image_quality: int = 90
    note_max_chars: int = NOTE_MAX_CHARS


@dataclass(frozen=True)
class PromptSpec:
    system: str
    user_template: str
    tool: dict[str, Any]

    def user_text(self, question: str) -> str:
        # str.replace, not str.format: the template holds literal JSON braces.
        return self.user_template.replace("{question}", question)


@dataclass(frozen=True)
class FakeProfile:
    accuracy: Mapping[str, float]
    malformed_rate: float = 0.0


@dataclass(frozen=True)
class ModelsConfig:
    models: tuple[ModelSpec, ...]
    settings: Settings
    prompt: PromptSpec
    fake_profiles: dict[str, FakeProfile]

    def spec(self, model_id: str) -> ModelSpec | None:
        for m in self.models:
            if m.id == model_id:
                return m
        return None

    def model_ids(self) -> list[str]:
        return [m.id for m in self.models]


def load_models_config(path: Path = MODELS_YAML) -> ModelsConfig:
    with path.open(encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    models = tuple(
        ModelSpec(
            id=str(m["id"]),
            short=str(m.get("short", m["id"])),
            confirmed_against_models_page=bool(m.get("confirmed_against_models_page", False)),
            accepts_temperature=bool(m.get("accepts_temperature", False)),
        )
        for m in doc["models"]
    )
    s = doc.get("settings", {})
    settings = Settings(
        temperature=float(s.get("temperature", 0.0)),
        max_tokens=int(s.get("max_tokens", 2048)),
        runs=int(s.get("runs", 3)),
        resize_long_side_px=int(s.get("resize_long_side_px", 1092)),
        image_format=str(s.get("image_format", "JPEG")),
        image_quality=int(s.get("image_quality", 90)),
        note_max_chars=int(s.get("note_max_chars", NOTE_MAX_CHARS)),
    )
    p = doc["prompt"]
    prompt = PromptSpec(
        system=str(p["system"]), user_template=str(p["user_template"]), tool=p["tool"]
    )
    fakes = {
        str(model_id): FakeProfile(
            accuracy={str(k): float(v) for k, v in prof.get("accuracy", {}).items()},
            malformed_rate=float(prof.get("malformed_rate", 0.0)),
        )
        for model_id, prof in (doc.get("fake_profiles") or {}).items()
    }
    return ModelsConfig(models=models, settings=settings, prompt=prompt, fake_profiles=fakes)


@dataclass(frozen=True)
class ModelPrice:
    input_per_million: float
    output_per_million: float
    source_checked: bool


@dataclass(frozen=True)
class Pricing:
    models: dict[str, ModelPrice]
    batch_multiplier: float = 1.0
    batch_checked: bool = False

    def cost_usd(
        self, model_id: str, input_tokens: int, output_tokens: int, *, batch: bool
    ) -> float:
        price = self.models.get(model_id)
        if price is None:
            return 0.0
        raw = (
            input_tokens * price.input_per_million + output_tokens * price.output_per_million
        ) / 1_000_000
        return round(raw * (self.batch_multiplier if batch else 1.0), 8)

    def checked(self, model_id: str) -> bool:
        price = self.models.get(model_id)
        return price is not None and price.source_checked


def load_pricing(path: Path = PRICING_YAML) -> Pricing:
    with path.open(encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    models = {
        str(k): ModelPrice(
            input_per_million=float(v["input_per_million"]),
            output_per_million=float(v["output_per_million"]),
            source_checked=bool(v.get("source_checked", False)),
        )
        for k, v in doc["models"].items()
    }
    disc = doc.get("batch_discount", {})
    return Pricing(
        models=models,
        batch_multiplier=float(disc.get("multiplier", 1.0)),
        batch_checked=bool(disc.get("source_checked", False)),
    )


# ---------------------------------------------------------------------------------------------
# Items and photos


@dataclass(frozen=True)
class Item:
    id: str
    feature: str
    gold: str
    photo_id: str
    photo_path: Path
    is_placeholder: bool


def load_manifest(root: Path = ROOT) -> dict[str, dict[str, str]]:
    with (root / "photos" / "manifest.csv").open(newline="", encoding="utf-8") as f:
        return {row["id"]: row for row in csv.DictReader(f)}


def load_questions(root: Path = ROOT) -> dict[str, str]:
    """Feature id to question, word for word from content/features.yaml."""
    with (root / "content" / "features.yaml").open(encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    return {str(row["id"]): str(row["question"]) for row in doc["features"]}


def load_test_items(root: Path = ROOT) -> list[Item]:
    manifest = load_manifest(root)
    with (root / "content" / "test_items.yaml").open(encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    items: list[Item] = []
    for row in doc["items"]:
        photo = manifest[str(row["photo_id"])]
        items.append(
            Item(
                id=str(row["id"]),
                feature=str(row["feature"]),
                gold=str(row["gold"]),
                photo_id=str(row["photo_id"]),
                photo_path=root / "photos" / photo["file"],
                is_placeholder=photo["license"] == "placeholder",
            )
        )
    return items


def resize_long_side(
    image_bytes: bytes, long_side: int = 1092, *, fmt: str = "JPEG", quality: int = 90
) -> bytes:
    """Return the image with its longer side exactly long_side pixels, as JPEG bytes."""
    with Image.open(io.BytesIO(image_bytes)) as img:
        rgb = img.convert("RGB")
        w, h = rgb.size
        scale = long_side / max(w, h)
        size = (max(1, round(w * scale)), max(1, round(h * scale)))
        if size[0] >= size[1]:
            size = (long_side, size[1])
        else:
            size = (size[0], long_side)
        out = rgb.resize(size, Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        out.save(buf, fmt, quality=quality)
        return buf.getvalue()


def image_size(image_bytes: bytes) -> tuple[int, int]:
    with Image.open(io.BytesIO(image_bytes)) as img:
        return img.size


def is_correct(answer: TestAnswer, gold: str) -> bool:
    return (answer == "yes" and gold == "present") or (answer == "no" and gold == "absent")


# ---------------------------------------------------------------------------------------------
# Clients


@dataclass(frozen=True)
class RawAnswer:
    """One model reply before forcing. payload is the tool input, the text, or None."""

    payload: object
    model_id: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    stop_reason: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class Query:
    custom_id: str
    item_id: str
    feature: str
    question: str
    image_bytes: bytes
    model_id: str
    run: int


class Client(Protocol):
    real: bool

    def answer(self, image_bytes: bytes, question: str, model_id: str) -> RawAnswer: ...

    def answer_many(self, queries: Sequence[Query]) -> list[RawAnswer]: ...


class CostLog:
    """Appends one JSON line per call. With path None it keeps the lines in memory only."""

    def __init__(self, path: Path | None) -> None:
        self.path = path
        self.lines: list[dict[str, Any]] = []

    def append(
        self,
        *,
        model: str,
        purpose: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        real: bool,
    ) -> dict[str, Any]:
        line = {
            "ts_utc": now_utc(),
            "model": model,
            "purpose": purpose,
            "input_tokens": int(input_tokens),
            "output_tokens": int(output_tokens),
            "cost_usd": float(cost_usd),
            "real": bool(real),
        }
        self.lines.append(line)
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(line, sort_keys=True) + "\n")
        return line


_MALFORMED_SAMPLES: tuple[object, ...] = (
    "Yes, I think the banks are built.",
    '{"answer": "maybe", "note": "hard to say"}',
    '{"answer": "yes", "note": "cut off',
    "",
    None,
    '["yes"]',
    "answer: no",
    {"verdict": "no"},
    {"answer": 1, "note": "a number"},
)

FAKE_UNKNOWN_NOTE = "FAKE: this frame does not look like a stream, so I cannot tell."


class FakeClient:
    """Deterministic stand-in for a vision model. Spends nothing and knows nothing about photos.

    Answers for a registered item are drawn from the seed and the item id so a run repeats
    exactly. accuracy per feature is the chance of matching the gold label. An image that is
    not registered (the checker path, or an adversarial frame) gets unknown_answer.
    """

    real = False

    def __init__(
        self,
        *,
        seed: int,
        profiles: Mapping[str, FakeProfile],
        items: Sequence[Item] = (),
        unknown_answer: TestAnswer = "cant_tell",
        default_profile: FakeProfile | None = None,
        cost_log: CostLog | None = None,
        purpose: str = "model_sweep",
    ) -> None:
        self.seed = seed
        self.profiles = dict(profiles)
        self.items = {i.id: i for i in items}
        self.unknown_answer: TestAnswer = unknown_answer
        self.default_profile = default_profile or FakeProfile(accuracy={}, malformed_rate=0.0)
        self.cost_log = cost_log
        self.purpose = purpose
        self.calls = 0

    def _profile(self, model_id: str) -> FakeProfile:
        return self.profiles.get(model_id, self.default_profile)

    def _produce(self, identity: str, model_id: str, item: Item | None) -> RawAnswer:
        self.calls += 1
        rng = random.Random(f"{self.seed}|{model_id}|{identity}")
        profile = self._profile(model_id)
        payload: object
        if rng.random() < profile.malformed_rate:
            payload = rng.choice(_MALFORMED_SAMPLES)
        elif item is None:
            payload = {"answer": self.unknown_answer, "note": FAKE_UNKNOWN_NOTE}
        else:
            right: TestAnswer = "yes" if item.gold == "present" else "no"
            wrong: TestAnswer = "no" if item.gold == "present" else "yes"
            if rng.random() < profile.accuracy.get(item.feature, 0.5):
                answer: TestAnswer = right
            else:
                answer = rng.choice([wrong, wrong, "cant_tell"])
            payload = {
                "answer": answer,
                "note": f"FAKE: made up {answer} for {item.feature} on {item.id}, not a real look.",
            }
        raw = RawAnswer(payload=payload, model_id=model_id, stop_reason="end_turn")
        if self.cost_log is not None:
            self.cost_log.append(
                model=model_id,
                purpose=self.purpose,
                input_tokens=0,
                output_tokens=0,
                cost_usd=0.0,
                real=False,
            )
        return raw

    def answer(self, image_bytes: bytes, question: str, model_id: str) -> RawAnswer:
        identity = "img:" + hashlib.sha256(image_bytes).hexdigest()[:16]
        return self._produce(identity, model_id, None)

    def answer_many(self, queries: Sequence[Query]) -> list[RawAnswer]:
        return [self._produce(q.custom_id, q.model_id, self.items.get(q.item_id)) for q in queries]


class RealClientRefused(RuntimeError):
    """Raised with a plain sentence when the real client must not run."""


def raw_from_message(msg: Any, model_id: str, *, cost_usd: float = 0.0) -> RawAnswer:
    """Pull the tool input or the text out of an SDK Message, plus the usage fields."""
    payload: object = None
    texts: list[str] = []
    for block in getattr(msg, "content", []) or []:
        kind = getattr(block, "type", None)
        if kind == "tool_use" and getattr(block, "name", None) == "answer":
            payload = dict(getattr(block, "input", {}) or {})
            break
        if kind == "text":
            texts.append(str(getattr(block, "text", "")))
    if payload is None:
        payload = "\n".join(texts)
    usage = getattr(msg, "usage", None)
    return RawAnswer(
        payload=payload,
        model_id=model_id,
        input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
        output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
        cost_usd=cost_usd,
        stop_reason=getattr(msg, "stop_reason", None),
    )


class RealClient:
    """Paid vision model calls through the anthropic SDK. Refuses without a key or unchecked config.

    Single answers use messages.create. answer_many uses the Messages Batch API: create one
    batch, poll until it has ended, collect results by custom_id. Every call is logged.
    """

    real = True

    def __init__(
        self,
        *,
        api_key: str | None,
        config: ModelsConfig,
        pricing: Pricing,
        cost_log: CostLog | None = None,
        purpose: str = "model_sweep",
        sdk_client: Any | None = None,
        poll_seconds: float = 30.0,
        max_wait_seconds: float = 24 * 3600,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not api_key:
            raise RealClientRefused(REFUSAL_NO_KEY)
        self.config = config
        self.pricing = pricing
        self.cost_log = cost_log
        self.purpose = purpose
        self.poll_seconds = poll_seconds
        self.max_wait_seconds = max_wait_seconds
        self._sleep = sleep
        self._sdk = sdk_client if sdk_client is not None else self._make_sdk(api_key)

    @staticmethod
    def _make_sdk(api_key: str) -> Any:
        import anthropic

        return anthropic.Anthropic(api_key=api_key)

    def check_ready(self, model_id: str) -> None:
        spec = self.config.spec(model_id)
        if spec is None or not spec.confirmed_against_models_page:
            raise RealClientRefused(REFUSAL_UNCONFIRMED.format(model=model_id))
        if not self.pricing.checked(model_id):
            raise RealClientRefused(REFUSAL_UNPRICED.format(model=model_id))

    def build_params(self, model_id: str, image_bytes: bytes, question: str) -> dict[str, Any]:
        s = self.config.settings
        spec = self.config.spec(model_id)
        media = "image/jpeg" if s.image_format.upper() == "JPEG" else "image/png"
        params: dict[str, Any] = {
            "model": model_id,
            "max_tokens": s.max_tokens,
            "system": self.config.prompt.system,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media,
                                "data": base64.standard_b64encode(image_bytes).decode("ascii"),
                            },
                        },
                        {"type": "text", "text": self.config.prompt.user_text(question)},
                    ],
                }
            ],
            "tools": [self.config.prompt.tool],
            "tool_choice": {"type": "auto"},
        }
        if spec is not None and spec.accepts_temperature:
            params["temperature"] = s.temperature
        return params

    def _log(self, raw: RawAnswer) -> None:
        if self.cost_log is not None:
            self.cost_log.append(
                model=raw.model_id,
                purpose=self.purpose,
                input_tokens=raw.input_tokens,
                output_tokens=raw.output_tokens,
                cost_usd=raw.cost_usd,
                real=True,
            )

    def answer(self, image_bytes: bytes, question: str, model_id: str) -> RawAnswer:
        self.check_ready(model_id)
        msg = self._sdk.messages.create(**self.build_params(model_id, image_bytes, question))
        raw = raw_from_message(msg, model_id)
        raw = RawAnswer(
            **{
                **asdict(raw),
                "cost_usd": self.pricing.cost_usd(
                    model_id, raw.input_tokens, raw.output_tokens, batch=False
                ),
            }
        )
        self._log(raw)
        return raw

    def answer_many(self, queries: Sequence[Query]) -> list[RawAnswer]:
        for q in queries:
            self.check_ready(q.model_id)
        if not queries:
            return []
        # The Batch API takes a custom_id of letters, digits, _ and - only, 64 at most, so our
        # own ids (model|item|run) never go on the wire. Each query gets its position instead.
        wire = [f"q{index:05d}" for index in range(len(queries))]
        requests = [
            {
                "custom_id": wire_id,
                "params": self.build_params(q.model_id, q.image_bytes, q.question),
            }
            for wire_id, q in zip(wire, queries, strict=True)
        ]
        batch = self._sdk.messages.batches.create(requests=requests)
        waited = 0.0
        while getattr(batch, "processing_status", "") != "ended":
            if waited >= self.max_wait_seconds:
                raise RealClientRefused(
                    f"Batch {batch.id} did not end within {self.max_wait_seconds} seconds."
                )
            self._sleep(self.poll_seconds)
            waited += self.poll_seconds
            batch = self._sdk.messages.batches.retrieve(batch.id)
        by_id: dict[str, Any] = {}
        for result in self._sdk.messages.batches.results(batch.id):
            by_id[str(result.custom_id)] = result.result
        out: list[RawAnswer] = []
        for wire_id, q in zip(wire, queries, strict=True):
            result = by_id.get(wire_id)
            kind = getattr(result, "type", None)
            if kind == "succeeded":
                raw = raw_from_message(getattr(result, "message", None), q.model_id)
                raw = RawAnswer(
                    **{
                        **asdict(raw),
                        "cost_usd": self.pricing.cost_usd(
                            q.model_id, raw.input_tokens, raw.output_tokens, batch=True
                        ),
                    }
                )
            else:
                detail = "no result" if result is None else str(kind)
                raw = RawAnswer(payload=None, model_id=q.model_id, error=detail)
            self._log(raw)
            out.append(raw)
        return out


# ---------------------------------------------------------------------------------------------
# The sweep


@dataclass(frozen=True)
class AnswerRecord:
    model: str
    item_id: str
    feature: str
    gold: str
    run: int
    custom_id: str
    answer: TestAnswer
    note: str
    correct: bool
    malformed: bool
    reason: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    error: str | None
    raw: object


def _jsonable(payload: object) -> object:
    if payload is None or isinstance(payload, str | int | float | bool):
        return payload
    if isinstance(payload, Mapping):
        return {str(k): _jsonable(v) for k, v in payload.items()}
    if isinstance(payload, list | tuple):
        return [_jsonable(v) for v in payload]
    return repr(payload)


def build_queries(
    model_id: str,
    items: Sequence[Item],
    questions: Mapping[str, str],
    images: Mapping[str, bytes],
    *,
    runs: int,
) -> list[Query]:
    return [
        Query(
            custom_id=f"{model_id}|{item.id}|r{run}",
            item_id=item.id,
            feature=item.feature,
            question=questions[item.feature],
            image_bytes=images[item.id],
            model_id=model_id,
            run=run,
        )
        for run in range(runs)
        for item in items
    ]


def prepared_images(items: Sequence[Item], settings: Settings) -> dict[str, bytes]:
    """Every test photo resized once, keyed by item id."""
    cache: dict[str, bytes] = {}
    by_path: dict[Path, bytes] = {}
    for item in items:
        if item.photo_path not in by_path:
            by_path[item.photo_path] = resize_long_side(
                item.photo_path.read_bytes(),
                settings.resize_long_side_px,
                fmt=settings.image_format,
                quality=settings.image_quality,
            )
        cache[item.id] = by_path[item.photo_path]
    return cache


def record_from(q: Query, raw: RawAnswer, gold: str) -> AnswerRecord:
    forced: ForcedAnswer = force_answer(raw.payload)
    return AnswerRecord(
        model=q.model_id,
        item_id=q.item_id,
        feature=q.feature,
        gold=gold,
        run=q.run,
        custom_id=q.custom_id,
        answer=forced.answer,
        note=forced.note,
        correct=is_correct(forced.answer, gold),
        malformed=forced.malformed,
        reason=forced.reason if forced.malformed else "",
        input_tokens=raw.input_tokens,
        output_tokens=raw.output_tokens,
        cost_usd=raw.cost_usd,
        error=raw.error,
        raw=_jsonable(raw.payload),
    )


def run_sweep(
    client: Client,
    model_ids: Sequence[str],
    items: Sequence[Item],
    questions: Mapping[str, str],
    *,
    runs: int,
    settings: Settings,
    images: Mapping[str, bytes] | None = None,
) -> list[AnswerRecord]:
    imgs = images if images is not None else prepared_images(items, settings)
    gold = {i.id: i.gold for i in items}
    records: list[AnswerRecord] = []
    for model_id in model_ids:
        queries = build_queries(model_id, items, questions, imgs, runs=runs)
        raws = client.answer_many(queries)
        if len(raws) != len(queries):
            raise RuntimeError(f"{model_id}: {len(raws)} answers for {len(queries)} queries")
        records.extend(
            record_from(q, r, gold[q.item_id]) for q, r in zip(queries, raws, strict=True)
        )
    return records


def feature_passes(runs: Sequence[Sequence[bool]], *, needed: int = PASS_RUNS_NEEDED) -> bool:
    """Analysis plan item 8: all items right in at least `needed` of the runs."""
    return sum(1 for run in runs if len(run) == ITEMS_PER_FEATURE and all(run)) >= needed


def pass_table(
    records: Sequence[AnswerRecord],
    model_ids: Sequence[str],
    items: Sequence[Item],
    *,
    runs: int,
    real: bool,
) -> dict[str, Any]:
    correct = {(r.model, r.item_id, r.run): r.correct for r in records}
    models: dict[str, Any] = {}
    for model_id in model_ids:
        per_feature: dict[str, Any] = {}
        for feature in FEATURES:
            feature_items = [i for i in items if i.feature == feature]
            grid = [
                [bool(correct.get((model_id, i.id, run), False)) for i in feature_items]
                for run in range(runs)
            ]
            per_feature[feature] = {"passed": feature_passes(grid), "runs": grid}
        models[model_id] = per_feature
    doc: dict[str, Any] = {
        "real": real,
        "generated_at_utc": now_utc(),
        "synthetic": not real,
        "script": SCRIPT,
        "pass_rule": (
            "all 4 items of a feature right in at least 2 of 3 runs (docs/analysis_plan.md item 8)"
        ),
        "models": models,
    }
    if not real:
        doc["stamp"] = "SYNTHETIC"
    return doc


def item_accuracy(
    records: Sequence[AnswerRecord], model_ids: Sequence[str], items: Sequence[Item], *, real: bool
) -> dict[str, Any]:
    models: dict[str, dict[str, float]] = {}
    for model_id in model_ids:
        per_item: dict[str, float] = {}
        for item in items:
            hits = [r.correct for r in records if r.model == model_id and r.item_id == item.id]
            per_item[item.id] = round(sum(hits) / len(hits), 4) if hits else 0.0
        models[model_id] = per_item
    doc: dict[str, Any] = {
        "real": real,
        "synthetic": not real,
        "generated_at_utc": now_utc(),
        "script": SCRIPT,
        "models": models,
    }
    if not real:
        doc["stamp"] = "SYNTHETIC"
    return doc


def summary_lines(table: Mapping[str, Any]) -> list[str]:
    tag = "REAL" if table.get("real") else "SYNTHETIC (fake client, no model was called)"
    lines = [f"pass table: {tag}"]
    width = max(len(m) for m in table["models"]) if table["models"] else 10
    header = "model".ljust(width) + "  " + "  ".join(f.ljust(16) for f in FEATURES)
    lines.append(header)
    for model_id, per_feature in table["models"].items():
        cells = []
        for feature in FEATURES:
            entry = per_feature[feature]
            clean_runs = sum(1 for run in entry["runs"] if all(run))
            word = "pass" if entry["passed"] else "fail"
            cells.append(f"{word} {clean_runs}/{len(entry['runs'])} runs".ljust(16))
        lines.append(model_id.ljust(width) + "  " + "  ".join(cells))
    passed = sum(1 for per in table["models"].values() for e in per.values() if e["passed"])
    total = len(table["models"]) * len(FEATURES)
    lines.append(f"features passed: {passed} of {total}")
    return lines


# ---------------------------------------------------------------------------------------------
# Money


def load_env_file(path: Path) -> dict[str, str]:
    """KEY=VALUE lines from a .env file. Never prints values."""
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        key, _, value = s.partition("=")
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def api_key_from(env_file: Path, environ: Mapping[str, str]) -> str | None:
    key = load_env_file(env_file).get("ANTHROPIC_API_KEY") or environ.get("ANTHROPIC_API_KEY")
    return key or None


def estimate_cost(
    model_ids: Sequence[str],
    images: Mapping[str, bytes],
    pricing: Pricing,
    settings: Settings,
    *,
    runs: int,
) -> dict[str, float]:
    """Rough upper and expected cost of a real batch run. An estimate, not a measurement."""
    image_tokens = 0
    for data in images.values():
        w, h = image_size(data)
        image_tokens += (w * h) // 750
    calls = len(images) * runs
    in_tokens = (image_tokens + ESTIMATE_TEXT_TOKENS * len(images)) * runs
    expected = worst = 0.0
    for model_id in model_ids:
        expected += pricing.cost_usd(
            model_id, in_tokens, calls * ESTIMATE_OUTPUT_TOKENS, batch=True
        )
        worst += pricing.cost_usd(model_id, in_tokens, calls * settings.max_tokens, batch=True)
    return {"expected_usd": round(expected, 4), "worst_case_usd": round(worst, 4)}


# ---------------------------------------------------------------------------------------------
# Output


def now_utc() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, doc: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")


@dataclass
class SweepOutputs:
    pass_table: Path
    item_accuracy: Path
    sweep: Path
    cost_log: Path
    summary: list[str] = field(default_factory=list)


def write_outputs(
    results_dir: Path,
    records: Sequence[AnswerRecord],
    model_ids: Sequence[str],
    items: Sequence[Item],
    *,
    runs: int,
    real: bool,
    seed: int | None,
    config: ModelsConfig,
    images: Mapping[str, bytes],
) -> SweepOutputs:
    table = pass_table(records, model_ids, items, runs=runs, real=real)
    acc = item_accuracy(records, model_ids, items, real=real)
    sizes = sorted({image_size(b) for b in images.values()})
    sweep_doc: dict[str, Any] = {
        "real": real,
        "synthetic": not real,
        "generated_at_utc": now_utc(),
        "script": SCRIPT,
        "seed": seed,
        "runs": runs,
        "settings": {
            **asdict(config.settings),
            "models": [asdict(spec) for m in model_ids if (spec := config.spec(m)) is not None],
            "prompt_system": config.prompt.system,
            "prompt_user_template": config.prompt.user_template,
            "image_sizes_sent": [list(s) for s in sizes],
        },
        "counts": {
            "answers": len(records),
            "malformed": sum(1 for r in records if r.malformed),
            "errors": sum(1 for r in records if r.error),
            "cant_tell": sum(1 for r in records if r.answer == "cant_tell"),
            "cost_usd": round(sum(r.cost_usd for r in records), 6),
        },
        "answers": [asdict(r) for r in records],
    }
    if not real:
        sweep_doc["stamp"] = "SYNTHETIC"
    out = SweepOutputs(
        pass_table=results_dir / "model_pass_table.json",
        item_accuracy=results_dir / "model_item_accuracy.json",
        sweep=results_dir / f"model_sweep_{stamp()}.json",
        cost_log=results_dir / ("cost_log.jsonl" if real else "cost_log_fake.jsonl"),
    )
    write_json(out.pass_table, table)
    write_json(out.item_accuracy, acc)
    write_json(out.sweep, sweep_doc)
    out.summary = summary_lines(table)
    return out


# ---------------------------------------------------------------------------------------------
# CLI


def build_real_client(
    *,
    model_ids: Sequence[str],
    config: ModelsConfig,
    pricing: Pricing,
    cost_log: CostLog | None,
    env_file: Path,
    environ: Mapping[str, str],
    purpose: str = "model_sweep",
    poll_seconds: float = 30.0,
) -> tuple[RealClient | None, str]:
    """A ready RealClient, or (None, plain sentence saying why there is no real run)."""
    key = api_key_from(env_file, environ)
    if not key:
        return None, REFUSAL_NO_KEY
    try:
        client = RealClient(
            api_key=key,
            config=config,
            pricing=pricing,
            cost_log=cost_log,
            purpose=purpose,
            poll_seconds=poll_seconds,
        )
        for m in model_ids:
            client.check_ready(m)
    except RealClientRefused as e:
        return None, str(e)
    return client, ""


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--fake", action="store_true", help="fake client, spends nothing (default)")
    mode.add_argument("--real", action="store_true", help="paid Batch API run, needs a key in .env")
    p.add_argument("--seed", type=int, default=DEFAULT_SEED, help="seed for the fake client")
    p.add_argument("--runs", type=int, default=None, help="repeat runs, default from models.yaml")
    p.add_argument("--models", nargs="*", default=None, help="subset of model ids")
    p.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS)
    p.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    p.add_argument("--max-usd", type=float, default=5.0, help="refuse a real run above this")
    p.add_argument("--poll-seconds", type=float, default=30.0)
    return p.parse_args(argv)


def main(argv: Sequence[str] | None = None, *, environ: Mapping[str, str] | None = None) -> int:
    args = parse_args(argv)
    env = environ if environ is not None else os.environ
    config = load_models_config()
    pricing = load_pricing()
    model_ids = list(args.models) if args.models else config.model_ids()
    unknown = [m for m in model_ids if config.spec(m) is None]
    if unknown:
        print(f"Unknown model ids, not in evals/models.yaml: {', '.join(unknown)}")
        return 2
    runs = args.runs or config.settings.runs
    items = load_test_items()
    questions = load_questions()
    images = prepared_images(items, config.settings)
    log_name = "cost_log.jsonl" if args.real else "cost_log_fake.jsonl"
    cost_log = CostLog(args.results_dir / log_name)

    client: Client
    if args.real:
        real_client, why_not = build_real_client(
            model_ids=model_ids,
            config=config,
            pricing=pricing,
            cost_log=cost_log,
            env_file=args.env_file,
            environ=env,
            poll_seconds=args.poll_seconds,
        )
        if real_client is None:
            print(why_not)
            return 2
        est = estimate_cost(model_ids, images, pricing, config.settings, runs=runs)
        if est["worst_case_usd"] > args.max_usd:
            print(REFUSAL_OVER_CAP.format(cost=est["worst_case_usd"], cap=args.max_usd))
            return 2
        print(
            f"real run: {len(model_ids)} models, {len(items)} items, {runs} runs; "
            f"expected about {est['expected_usd']:.2f} USD, "
            f"worst case {est['worst_case_usd']:.2f} USD"
        )
        client = real_client
        seed: int | None = None
    else:
        placeholders = sum(1 for i in items if i.is_placeholder)
        print(
            f"fake run: seed {args.seed}, {len(model_ids)} models, {len(items)} items "
            f"({placeholders} placeholders), {runs} runs. No model is called and nothing is spent."
        )
        client = FakeClient(
            seed=args.seed, profiles=config.fake_profiles, items=items, cost_log=cost_log
        )
        seed = args.seed

    records = run_sweep(
        client, model_ids, items, questions, runs=runs, settings=config.settings, images=images
    )
    out = write_outputs(
        args.results_dir,
        records,
        model_ids,
        items,
        runs=runs,
        real=args.real,
        seed=seed,
        config=config,
        images=images,
    )
    print("\n".join(out.summary))
    malformed = sum(1 for r in records if r.malformed)
    print(
        f"answers: {len(records)}, malformed forced to cant_tell: {malformed}, "
        f"cost logged: {sum(r.cost_usd for r in records):.4f} USD"
    )
    if not args.real:
        est = estimate_cost(model_ids, images, pricing, config.settings, runs=runs)
        print(
            f"estimate for the same run for real, from unchecked prices: about "
            f"{est['expected_usd']:.2f} USD, worst case {est['worst_case_usd']:.2f} USD"
        )
    print(f"wrote {out.pass_table}")
    print(f"wrote {out.item_accuracy.name}, {out.sweep.name}, appended {out.cost_log.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
