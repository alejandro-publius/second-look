"""Pick the three README examples by the plan's rule (docs/analysis_plan.md item 9).

The three test items with the largest gap between trained-arm accuracy and the best model's
accuracy, in either direction. Reads results/model_item_accuracy.json (W6 writes it) and the
usability results, writes results/examples.json. If the model file is missing, a SYNTHETIC one is
written so the pipeline can be tested end to end.

Usage: uv run python evals/pick_examples.py --synthetic
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

from evals.common import PLAN_SEED, RESULTS_DIR, load_test_items, result_header, write_json

SCRIPT = "evals/pick_examples.py"
N_EXAMPLES = 3
MODEL_FILE = "model_item_accuracy.json"
FAKE_MODELS = ("fake-vision-a", "fake-vision-b")


def synthetic_model_accuracy(seed: int = PLAN_SEED) -> dict[str, Any]:
    """A stand-in for W6's file: two fake models with made-up accuracy, stamped SYNTHETIC."""
    rng = np.random.default_rng(seed)
    items = load_test_items()
    models: dict[str, dict[str, float]] = {}
    for name in FAKE_MODELS:
        base = rng.uniform(0.45, 0.85)
        models[name] = {
            row["id"]: round(float(np.clip(base + rng.normal(0, 0.25), 0.0, 1.0)), 3)
            for row in items
        }
    out = result_header(SCRIPT, synthetic=True, stamp="SYNTHETIC")
    out["real"] = False
    out["note"] = "placeholder written by pick_examples.py because W6's file was missing"
    out["models"] = models
    return out


def load_model_accuracy(path: Path, *, synthetic: bool, allow_write: bool) -> dict[str, Any]:
    if path.exists():
        doc = json.loads(path.read_text(encoding="utf-8"))
        if not synthetic and (doc.get("synthetic") or not doc.get("real", False)):
            raise SystemExit(
                f"{path} is synthetic or not marked real; pass --synthetic or run the real sweep."
            )
        return doc
    if not synthetic:
        raise SystemExit(f"{path} is missing. W6's model sweep writes it. Nothing picked.")
    doc = synthetic_model_accuracy()
    if allow_write:
        write_json(path, doc)
        print(f"wrote SYNTHETIC placeholder {path}")
    return doc


def newest_real_usability(results_dir: Path) -> Path | None:
    candidates = sorted(results_dir.glob("usability_*.json"), reverse=True)
    for path in candidates:
        doc = json.loads(path.read_text(encoding="utf-8"))
        if not doc.get("synthetic", True):
            return path
    return None


def best_model(models: dict[str, dict[str, float]]) -> tuple[str, float]:
    """The model with the highest mean accuracy over the 16 items. Ties go to the first name."""
    if not models:
        raise ValueError("no models in the model accuracy file")
    scored = {name: float(np.mean(list(acc.values()))) for name, acc in models.items() if acc}
    name = max(sorted(scored), key=lambda k: scored[k])
    return name, scored[name]


def pick(
    per_item: dict[str, Any], model_acc: dict[str, float], *, n: int = N_EXAMPLES
) -> list[dict[str, Any]]:
    """Rank items by |trained accuracy minus model accuracy|; largest first, item id breaks ties."""
    rows: list[dict[str, Any]] = []
    for item_id, entry in per_item.items():
        trained = entry.get("trained")
        model = model_acc.get(item_id)
        if trained is None or model is None:
            continue
        gap = float(trained) - float(model)
        rows.append(
            {
                "item_id": item_id,
                "feature": entry.get("feature"),
                "gold": entry.get("gold"),
                "photo_id": entry.get("photo_id"),
                "trained_accuracy": round(float(trained), 4),
                "model_accuracy": round(float(model), 4),
                "gap_points": round(gap * 100, 1),
                "direction": "people ahead" if gap > 0 else ("model ahead" if gap < 0 else "tie"),
            }
        )
    rows.sort(key=lambda r: (-abs(r["gap_points"]), r["item_id"]))
    return rows[:n]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument("--usability", type=Path, default=None, help="usability results JSON")
    parser.add_argument("--model-file", type=Path, default=None)
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    results_dir: Path = args.results_dir
    model_path = args.model_file if args.model_file is not None else results_dir / MODEL_FILE
    out_path = args.out if args.out is not None else results_dir / "examples.json"

    if args.usability is not None:
        usability_path = args.usability
    elif args.synthetic:
        usability_path = results_dir / "usability_synthetic.json"
    else:
        found = newest_real_usability(results_dir)
        if found is None:
            print(
                "No real usability results in results/. "
                "Run evals/usability_analysis.py after the lock."
            )
            return 3
        usability_path = found
    if not usability_path.exists():
        print(f"{usability_path} is missing. Run evals/usability_analysis.py --synthetic first.")
        return 4

    usability = json.loads(usability_path.read_text(encoding="utf-8"))
    if not args.synthetic and usability.get("synthetic"):
        print(f"{usability_path} is synthetic. Pass --synthetic or run the real analysis.")
        return 5
    models_doc = load_model_accuracy(model_path, synthetic=args.synthetic, allow_write=True)
    name, mean_acc = best_model(models_doc["models"])
    examples = pick(usability["per_item"], models_doc["models"][name])

    synthetic = bool(args.synthetic or usability.get("synthetic") or models_doc.get("synthetic"))
    result = result_header(SCRIPT, synthetic=synthetic, stamp=usability.get("stamp", "unknown"))
    result.update(
        {
            "rule": (
                "the three test items with the largest gap between trained-arm accuracy "
                "and the best model's accuracy, in either direction"
            ),
            "best_model": {"model_id": name, "mean_accuracy": round(mean_acc, 4)},
            "inputs": {"usability": str(usability_path), "model_item_accuracy": str(model_path)},
            "examples": examples,
        }
    )
    write_json(out_path, result)
    label = result["stamp"]
    picked = ", ".join(
        f"{e['item_id']} ({e['direction']}, gap {e['gap_points']} points)" for e in examples
    )
    print(f"{label}: best model {name} (mean accuracy {mean_acc:.3f}); picked {picked}")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
