"""Ablation: rules only, context only, vision only, all three (master brief section 10).

This fixes the shape of the comparison before real rules and real site context exist. The rules
and the context are stubs with a set accuracy, the vision signal is the fake client, and the
combination is a plain vote. Two pieces are real and stay when the stubs go: a blank or near
blank frame gets cant_tell from the rules, and in wet weather a yes on pipe_running is downgraded
to cant_tell, because rain makes any pipe run.

Run: uv run python evals/ablation.py --synthetic
Writes results/ablation_<stamp>.json, stamped SYNTHETIC. Fake calls go to results/cost_log.jsonl.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import random
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from PIL import Image, ImageStat

from core.checker import force_answer
from core.records import FEATURES, TestAnswer
from evals.benchmark import accuracy_cell
from evals.fixtures import adversarial_frames
from evals.model_sweep import (
    DEFAULT_RESULTS,
    DEFAULT_SEED,
    CostLog,
    FakeClient,
    FakeProfile,
    Item,
    Query,
    is_correct,
    load_models_config,
    load_questions,
    load_test_items,
    now_utc,
    prepared_images,
    stamp,
    write_json,
)

SCRIPT = "evals/ablation.py"
CONDITIONS: tuple[str, ...] = ("rules_only", "context_only", "vision_only", "all_three")
Rain = Literal["dry", "wet", "unknown"]
BLANK_STD_MAX = 4.0


def frame_is_blank(image_bytes: bytes) -> bool:
    """True for a flat frame: every channel varies by less than a few grey levels."""
    with Image.open(io.BytesIO(image_bytes)) as img:
        stat = ImageStat.Stat(img.convert("RGB"))
    return max(stat.stddev) < BLANK_STD_MAX


@dataclass(frozen=True)
class SiteContext:
    rain: Rain
    dry_days: int | None = None


def synthetic_context(seed: int, item_id: str) -> SiteContext:
    rng = random.Random(f"{seed}|context|{item_id}")
    if rng.random() < 0.6:
        return SiteContext(rain="dry", dry_days=rng.randint(3, 20))
    return SiteContext(rain="wet", dry_days=0)


class RuleStub:
    """Stand-in for image rules. The blank frame check is real; the rest is a planted guess."""

    def __init__(self, *, seed: int, accuracy: Mapping[str, float]) -> None:
        self.seed = seed
        self.accuracy = dict(accuracy)

    def answer(self, image_bytes: bytes, feature: str, gold: str | None) -> TestAnswer:
        if frame_is_blank(image_bytes) or gold is None:
            return "cant_tell"
        digest = hashlib.sha256(image_bytes).hexdigest()[:16]
        rng = random.Random(f"{self.seed}|rules|{feature}|{digest}")
        right: TestAnswer = "yes" if gold == "present" else "no"
        wrong: TestAnswer = "no" if gold == "present" else "yes"
        return right if rng.random() < self.accuracy.get(feature, 0.5) else wrong


class ContextStub:
    """Stand-in for site context. Only speaks about pipes, and only in dry weather."""

    def __init__(self, *, seed: int, accuracy: float = 0.5) -> None:
        self.seed = seed
        self.accuracy = accuracy

    def answer(self, site: SiteContext, feature: str, gold: str | None, key: str) -> TestAnswer:
        if feature != "pipe_running" or site.rain != "dry" or gold is None:
            return "cant_tell"
        rng = random.Random(f"{self.seed}|context|{key}")
        right: TestAnswer = "yes" if gold == "present" else "no"
        wrong: TestAnswer = "no" if gold == "present" else "yes"
        return right if rng.random() < self.accuracy else wrong


def wet_weather_rule(answer: TestAnswer, feature: str, site: SiteContext) -> TestAnswer:
    """A running pipe in the rain proves nothing, so a yes becomes cant_tell."""
    if feature == "pipe_running" and site.rain == "wet" and answer == "yes":
        return "cant_tell"
    return answer


def combine(
    rules: TestAnswer, context: TestAnswer, vision: TestAnswer, *, feature: str, site: SiteContext
) -> TestAnswer:
    """Plain vote. cant_tell abstains. A tie goes to vision if it voted, else cant_tell."""
    votes = [v for v in (rules, context, vision) if v != "cant_tell"]
    if not votes:
        return "cant_tell"
    yes = sum(1 for v in votes if v == "yes")
    no = len(votes) - yes
    if yes > no:
        out: TestAnswer = "yes"
    elif no > yes:
        out = "no"
    else:
        out = vision if vision != "cant_tell" else "cant_tell"
    return wet_weather_rule(out, feature, site)


@dataclass(frozen=True)
class Signals:
    rules: TestAnswer
    context: TestAnswer
    vision: TestAnswer
    site: SiteContext

    def by_condition(self, feature: str) -> dict[str, TestAnswer]:
        return {
            "rules_only": self.rules,
            "context_only": self.context,
            "vision_only": self.vision,
            "all_three": combine(
                self.rules, self.context, self.vision, feature=feature, site=self.site
            ),
        }


def signals_for(
    *,
    image_bytes: bytes,
    feature: str,
    gold: str | None,
    key: str,
    site: SiteContext,
    rules: RuleStub,
    context: ContextStub,
    vision: FakeClient,
    model_id: str,
    question: str,
    query: Query | None = None,
) -> Signals:
    raw = (
        vision.answer_many([query])[0]
        if query is not None
        else vision.answer(image_bytes, question, model_id)
    )
    return Signals(
        rules=rules.answer(image_bytes, feature, gold),
        context=context.answer(site, feature, gold, key),
        vision=force_answer(raw.payload).answer,
        site=site,
    )


def run_ablation(
    items: Sequence[Item],
    images: Mapping[str, bytes],
    questions: Mapping[str, str],
    *,
    seed: int,
    model_id: str,
    vision: FakeClient,
    rules: RuleStub,
    context: ContextStub,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    hits: dict[str, dict[str, list[bool]]] = {c: {f: [] for f in FEATURES} for c in CONDITIONS}
    rows: list[dict[str, Any]] = []
    for item in items:
        site = synthetic_context(seed, item.id)
        query = Query(
            custom_id=f"{model_id}|{item.id}|ablation",
            item_id=item.id,
            feature=item.feature,
            question=questions[item.feature],
            image_bytes=images[item.id],
            model_id=model_id,
            run=0,
        )
        sig = signals_for(
            image_bytes=images[item.id],
            feature=item.feature,
            gold=item.gold,
            key=item.id,
            site=site,
            rules=rules,
            context=context,
            vision=vision,
            model_id=model_id,
            question=questions[item.feature],
            query=query,
        )
        answers = sig.by_condition(item.feature)
        for cond, ans in answers.items():
            hits[cond][item.feature].append(is_correct(ans, item.gold))
        rows.append(
            {"item_id": item.id, "feature": item.feature, "gold": item.gold, "rain": site.rain}
            | answers
        )
    table: dict[str, dict[str, Any]] = {}
    for cond in CONDITIONS:
        cells: dict[str, Any] = {}
        all_hits: list[bool] = []
        for feature in FEATURES:
            h = hits[cond][feature]
            all_hits.extend(h)
            cells[feature] = accuracy_cell(sum(h), len(h))
        cells["all"] = accuracy_cell(sum(all_hits), len(all_hits))
        table[cond] = cells
    return table, rows


def adversarial_check(
    *,
    questions: Mapping[str, str],
    rules: RuleStub,
    context: ContextStub,
    vision: FakeClient,
    model_id: str,
) -> dict[str, dict[str, dict[str, TestAnswer]]]:
    """Every adversarial frame under every condition and feature. No gold, so no guess."""
    out: dict[str, dict[str, dict[str, TestAnswer]]] = {}
    for name, data in adversarial_frames().items():
        out[name] = {}
        for feature in FEATURES:
            sig = signals_for(
                image_bytes=data,
                feature=feature,
                gold=None,
                key=name,
                site=SiteContext(rain="dry", dry_days=7),
                rules=rules,
                context=context,
                vision=vision,
                model_id=model_id,
                question=questions[feature],
            )
            out[name][feature] = sig.by_condition(feature)
    return out


def table_lines(table: Mapping[str, Mapping[str, Any]]) -> list[str]:
    lines = ["ablation: SYNTHETIC (stubs and the fake client)"]
    lines.append("condition".ljust(14) + "  " + "  ".join(f.ljust(22) for f in (*FEATURES, "all")))
    for cond, cells in table.items():
        parts = []
        for key in (*FEATURES, "all"):
            c = cells[key]
            lo, hi = c["wilson_95"]
            parts.append(f"{c['accuracy']:.2f} [{lo:.2f}, {hi:.2f}] n={c['n']}".ljust(22))
        lines.append(cond.ljust(14) + "  " + "  ".join(parts))
    return lines


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--synthetic", action="store_true", required=True, help="stubs, fake client")
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--model", default=None, help="model id for the vision signal")
    p.add_argument("--rules-accuracy", type=float, default=0.65)
    p.add_argument("--context-accuracy", type=float, default=0.5)
    p.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS)
    return p.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    config = load_models_config()
    model_id = args.model or config.model_ids()[-1]
    if config.spec(model_id) is None:
        print(f"Unknown model id {model_id}, not in evals/models.yaml.")
        return 2
    items = load_test_items()
    questions = load_questions()
    images = prepared_images(items, config.settings)
    cost_log = CostLog(args.results_dir / "cost_log.jsonl")
    vision = FakeClient(
        seed=args.seed,
        profiles=config.fake_profiles,
        items=items,
        cost_log=cost_log,
        purpose="ablation",
        default_profile=FakeProfile(accuracy=dict.fromkeys(FEATURES, 0.9)),
    )
    rules = RuleStub(seed=args.seed, accuracy=dict.fromkeys(FEATURES, args.rules_accuracy))
    context = ContextStub(seed=args.seed, accuracy=args.context_accuracy)
    table, rows = run_ablation(
        items,
        images,
        questions,
        seed=args.seed,
        model_id=model_id,
        vision=vision,
        rules=rules,
        context=context,
    )
    adversarial = adversarial_check(
        questions=questions, rules=rules, context=context, vision=vision, model_id=model_id
    )
    flagged = [
        f"{frame}/{feature}/{cond}"
        for frame, per_feature in adversarial.items()
        for feature, per_cond in per_feature.items()
        for cond, ans in per_cond.items()
        if ans == "yes"
    ]
    doc: dict[str, Any] = {
        "generated_at_utc": now_utc(),
        "script": SCRIPT,
        "synthetic": True,
        "stamp": "SYNTHETIC",
        "stubs": True,
        "note": (
            "The rules and the context are stubs with a set accuracy and the vision signal is the "
            "fake client. Only the shape of the comparison is real."
        ),
        "seed": args.seed,
        "vision_model": model_id,
        "rules_accuracy_planted": args.rules_accuracy,
        "context_accuracy_planted": args.context_accuracy,
        "conditions": table,
        "per_item": rows,
        "adversarial": adversarial,
        "adversarial_yes_answers": flagged,
    }
    out = args.results_dir / f"ablation_{stamp()}.json"
    write_json(out, doc)
    print("\n".join(table_lines(table)))
    print(
        f"adversarial frames: {len(adversarial)} frames x {len(FEATURES)} features x "
        f"{len(CONDITIONS)} conditions, yes answers: {len(flagged)}"
    )
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
