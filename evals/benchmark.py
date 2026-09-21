"""Benchmark: per-feature accuracy per model over the labelled photo pool (master brief section 10).

The pool is every manifest row with role benchmark or test and a gold label of present or absent.
It runs on whatever is labelled. Each accuracy comes with a Wilson 95 percent interval, and the
JSON says how many photos stand behind it, because 16 or 40 photos is a small set.

Run: uv run python evals/benchmark.py --synthetic
         fake client on the placeholders, stamped SYNTHETIC
     uv run python evals/benchmark.py --real
         Batch API, refuses without a key in .env

Writes results/benchmark_<stamp>.json. Appends one line per call to results/cost_log.jsonl.
"""

from __future__ import annotations

import argparse
import math
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from core.records import FEATURES
from evals.model_sweep import (
    DEFAULT_ENV_FILE,
    DEFAULT_RESULTS,
    DEFAULT_SEED,
    ROOT,
    AnswerRecord,
    Client,
    CostLog,
    FakeClient,
    Item,
    build_real_client,
    load_manifest,
    load_models_config,
    load_pricing,
    load_questions,
    now_utc,
    prepared_images,
    run_sweep,
    stamp,
    write_json,
)

SCRIPT = "evals/benchmark.py"
POOL_ROLES = frozenset({"benchmark", "test"})
GOLD_VALUES = frozenset({"present", "absent"})
Z_95 = 1.959963984540054


def wilson_interval(correct: int, n: int, *, z: float = Z_95) -> tuple[float, float]:
    """Wilson score interval for a share. n of 0 gives the whole range."""
    if n <= 0:
        return (0.0, 1.0)
    p = correct / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def labelled_pool(manifest: Mapping[str, Mapping[str, str]], root: Path = ROOT) -> list[Item]:
    """Benchmark or test rows with a known feature and a present or absent label."""
    pool: list[Item] = []
    for row in manifest.values():
        if row.get("role") not in POOL_ROLES:
            continue
        if row.get("gold_label") not in GOLD_VALUES or row.get("feature") not in FEATURES:
            continue
        pool.append(
            Item(
                id=row["id"],
                feature=row["feature"],
                gold=row["gold_label"],
                photo_id=row["id"],
                photo_path=root / "photos" / row["file"],
                is_placeholder=row.get("license") == "placeholder",
            )
        )
    return pool


def skipped_rows(manifest: Mapping[str, Mapping[str, str]]) -> int:
    """Benchmark or test rows left out for want of a label or a feature."""
    return sum(
        1
        for row in manifest.values()
        if row.get("role") in POOL_ROLES
        and (row.get("gold_label") not in GOLD_VALUES or row.get("feature") not in FEATURES)
    )


def accuracy_cell(correct: int, n: int) -> dict[str, Any]:
    lo, hi = wilson_interval(correct, n)
    return {
        "n": n,
        "correct": correct,
        "accuracy": round(correct / n, 4) if n else None,
        "wilson_95": [round(lo, 4), round(hi, 4)],
    }


def per_feature_accuracy(
    records: Sequence[AnswerRecord], model_ids: Sequence[str]
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for model_id in model_ids:
        mine = [r for r in records if r.model == model_id]
        cells: dict[str, Any] = {}
        for feature in FEATURES:
            rows = [r for r in mine if r.feature == feature]
            cells[feature] = accuracy_cell(sum(r.correct for r in rows), len(rows))
        cells["all"] = accuracy_cell(sum(r.correct for r in mine), len(mine))
        cells["cant_tell_share"] = (
            round(sum(1 for r in mine if r.answer == "cant_tell") / len(mine), 4) if mine else None
        )
        cells["malformed"] = sum(1 for r in mine if r.malformed)
        out[model_id] = cells
    return out


def table_lines(models: Mapping[str, Mapping[str, Any]], *, synthetic: bool) -> list[str]:
    tag = "SYNTHETIC (fake client)" if synthetic else "REAL"
    lines = [f"benchmark: {tag}"]
    width = max((len(m) for m in models), default=10)
    lines.append("model".ljust(width) + "  " + "  ".join(f.ljust(22) for f in (*FEATURES, "all")))
    for model_id, cells in models.items():
        parts = []
        for key in (*FEATURES, "all"):
            c = cells[key]
            if c["n"]:
                lo, hi = c["wilson_95"]
                parts.append(f"{c['accuracy']:.2f} [{lo:.2f}, {hi:.2f}] n={c['n']}".ljust(22))
            else:
                parts.append("no photos".ljust(22))
        lines.append(model_id.ljust(width) + "  " + "  ".join(parts))
    return lines


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--synthetic", action="store_true", help="fake client, stamped SYNTHETIC")
    mode.add_argument("--real", action="store_true", help="paid Batch API run")
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--runs", type=int, default=1, help="repeat runs per photo")
    p.add_argument("--models", nargs="*", default=None)
    p.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS)
    p.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    p.add_argument("--poll-seconds", type=float, default=30.0)
    return p.parse_args(argv)


def main(argv: Sequence[str] | None = None, *, environ: Mapping[str, str] | None = None) -> int:
    args = parse_args(argv)
    env = environ if environ is not None else os.environ
    config = load_models_config()
    pricing = load_pricing()
    model_ids = list(args.models) if args.models else config.model_ids()
    manifest = load_manifest()
    pool = labelled_pool(manifest)
    skipped = skipped_rows(manifest)
    if not pool:
        print("No labelled benchmark or test photos in photos/manifest.csv, so nothing to score.")
        return 1
    questions = load_questions()
    images = prepared_images(pool, config.settings)
    cost_log = CostLog(args.results_dir / "cost_log.jsonl")
    placeholders = sum(1 for i in pool if i.is_placeholder)

    client: Client
    if args.real:
        real_client, why_not = build_real_client(
            model_ids=model_ids,
            config=config,
            pricing=pricing,
            cost_log=cost_log,
            env_file=args.env_file,
            environ=env,
            purpose="benchmark",
            poll_seconds=args.poll_seconds,
        )
        if real_client is None:
            print(why_not)
            return 2
        if placeholders:
            print(
                f"{placeholders} of {len(pool)} pool photos are gray placeholders, "
                "so a real run would spend money on nothing. Swap in real photos first."
            )
            return 2
        client = real_client
    else:
        client = FakeClient(
            seed=args.seed,
            profiles=config.fake_profiles,
            items=pool,
            cost_log=cost_log,
            purpose="benchmark",
        )
    synthetic = not args.real
    print(
        f"benchmark pool: {len(pool)} labelled photos ({placeholders} placeholders), "
        f"{skipped} pool rows skipped for want of a label, "
        f"{len(model_ids)} models, {args.runs} run(s)"
    )
    records = run_sweep(
        client, model_ids, pool, questions, runs=args.runs, settings=config.settings, images=images
    )
    models = per_feature_accuracy(records, model_ids)
    doc: dict[str, Any] = {
        "generated_at_utc": now_utc(),
        "script": SCRIPT,
        "synthetic": synthetic,
        "real": args.real,
        "seed": None if args.real else args.seed,
        "runs": args.runs,
        "pool": {
            "n_photos": len(pool),
            "n_placeholders": placeholders,
            "skipped_unlabelled": skipped,
            "by_feature": {f: sum(1 for i in pool if i.feature == f) for f in FEATURES},
            "photo_ids": [i.id for i in pool],
        },
        "interval": "Wilson score, 95 percent",
        "small_set_note": (
            f"{len(pool)} photos is a small set. Read the intervals, not the point estimates."
        ),
        "models": models,
        "cost_usd": round(sum(r.cost_usd for r in records), 6),
    }
    if synthetic:
        doc["stamp"] = "SYNTHETIC"
    out = args.results_dir / f"benchmark_{stamp()}.json"
    write_json(out, doc)
    print("\n".join(table_lines(models, synthetic=synthetic)))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
