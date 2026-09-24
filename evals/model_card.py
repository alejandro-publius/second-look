"""The counts behind docs/MODEL_CARD.md that no other results file holds.

What it counts, all read from committed files with no model call and no network:

1. How each model answered, per feature, in the sweep that wrote the pass table. The sweep is
   found by its time stamp, which must equal the pass table's. It shows, for example, how many
   answers on the plant photos were "can't tell".
2. What the paid calls cost, summed from results/cost_log.jsonl, one line per call. Lines from
   a fake client say `"real": false` and are counted apart.
3. The newest real benchmark's Wilson intervals in whole percent, copied from its own file, with
   each model's right answers on the photos that are not plants, and the score a checker would
   get by always answering No, from the answer key, so the counts can be read (critic round 01).
4. What one footage call cost, by model, in cents: one model answering about one frame.
5. How many of the flags the gate kept on the footage run are on each feature, worked out again
   from the run's raw answers through the gate (evals/footage_example.py load_run), because the
   creek check asks about only some of them (critic round 06, H02).

Run: uv run python evals/model_card.py            writes results/model_card.json
     uv run python evals/model_card.py --check    fails unless the committed file is what it writes
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from evals import footage_example

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "model_card.json"
ANSWERS = ("yes", "no", "cant_tell")


class SweepNotFound(Exception):
    """No committed sweep has the pass table's time stamp."""


def sweep_for(results: Path, table: dict[str, Any]) -> Path:
    stamp = table.get("generated_at_utc")
    for path in sorted(results.glob("model_sweep_*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        if doc.get("generated_at_utc") == stamp and doc.get("real") is True:
            return path
    raise SweepNotFound(f"no real sweep in results/ has the pass table's time stamp {stamp}")


def tally(answers: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(str(a.get("answer")) for a in answers)
    return {
        "answers": len(answers),
        **{answer: counts.get(answer, 0) for answer in ANSWERS},
        "correct": sum(1 for a in answers if a.get("correct") is True),
        "malformed": sum(1 for a in answers if a.get("malformed") is True),
    }


def cost(log: Path) -> dict[str, Any]:
    rows = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line]
    real = [r for r in rows if r.get("real") is True]
    by_purpose: dict[str, float] = {}
    for r in real:
        purpose = str(r.get("purpose", "unknown"))
        by_purpose[purpose] = by_purpose.get(purpose, 0.0) + float(r.get("cost_usd", 0.0))
    times = sorted(str(r.get("ts_utc", "")) for r in real)
    return {
        "log": log.relative_to(log.parents[1]).as_posix(),
        "calls": len(rows),
        "real_calls": len(real),
        "fake_calls": len(rows) - len(real),
        "real_usd": round(sum(float(r.get("cost_usd", 0.0)) for r in real), 4),
        "real_usd_by_purpose": {k: round(v, 4) for k, v in sorted(by_purpose.items())},
        "first_real_call_utc": times[0] if times else None,
        "last_real_call_utc": times[-1] if times else None,
        "footage_cents_per_call": per_call_cents(
            [r for r in real if r.get("purpose") == "footage"]
        ),
    }


def per_call_cents(rows: list[dict[str, Any]]) -> dict[str, float]:
    """The mean cost of one call, by model, in cents, to two decimals."""
    by_model: dict[str, list[float]] = {}
    for r in rows:
        by_model.setdefault(str(r.get("model")), []).append(float(r.get("cost_usd", 0.0)))
    return {m: round(100 * sum(v) / len(v), 2) for m, v in sorted(by_model.items()) if v}


def newest_real_benchmark(results: Path) -> Path | None:
    for path in sorted(results.glob("benchmark_*.json"), reverse=True):
        if json.loads(path.read_text(encoding="utf-8")).get("real") is True:
            return path
    return None


def percent(share: object) -> int | None:
    return round(float(share) * 100) if isinstance(share, int | float) else None


def benchmark(root: Path) -> dict[str, Any] | None:
    """The newest real benchmark, with each Wilson interval in whole percent.

    The shares in the benchmark file render to one decimal in a doc, which turns 0.953 into
    1.0. Whole percent keeps the interval readable: 10 of 12 is 55 to 95 percent.
    """
    path = newest_real_benchmark(root / "results")
    if path is None:
        return None
    doc = json.loads(path.read_text(encoding="utf-8"))
    models: dict[str, Any] = {}
    for model, row in sorted(doc.get("models", {}).items()):
        cells: dict[str, Any] = {}
        for key, cell in sorted(row.items()):
            if not isinstance(cell, dict) or "wilson_95" not in cell:
                continue
            low, high = cell["wilson_95"]
            cells[key] = {
                "correct": cell["correct"],
                "n": cell["n"],
                "low_pct": percent(low),
                "high_pct": percent(high),
            }
        cells["cant_tell_pct"] = percent(row.get("cant_tell_share"))
        rest = [c for k, c in row.items() if isinstance(c, dict) and k not in ("all", PLANT)]
        cells["without_plants"] = {
            "correct": sum(int(c["correct"]) for c in rest),
            "n": sum(int(c["n"]) for c in rest),
        }
        models[model] = cells
    runs = int(doc.get("runs") or 0)
    return {
        "file": path.relative_to(root).as_posix(),
        "runs": doc.get("runs"),
        "photos": doc.get("pool", {}).get("n_photos"),
        "interval": doc.get("interval"),
        "models": models,
        "always_no": always_no(root, runs),
    }


PLANT = "invasive_plant"


def always_no(root: Path, runs: int) -> dict[str, int]:
    """A checker that answers No to every photo gets every absent item right: the floor to beat."""
    items = yaml.safe_load((root / "content" / "test_items.yaml").read_text(encoding="utf-8"))
    golds = [str(i.get("gold")) for i in items.get("items", [])]
    return {"correct": runs * golds.count("absent"), "n": runs * len(golds)}


def footage_kept(root: Path) -> dict[str, Any] | None:
    """The footage run's kept flags by feature, from its raw file through the gate, or None when
    results/ holds no real footage run."""
    latest = root / footage_example.LATEST
    if not latest.is_file():
        return None
    if json.loads(latest.read_text(encoding="utf-8")).get("real") is not True:
        return None
    run = footage_example.load_run(root)
    return {
        "raw_answers": run.fixture.relative_to(root).as_posix(),
        "kept": run.counts["kept"],
        "by_feature": footage_example.kept_by_feature(run.found),
    }


def build(root: Path = ROOT) -> dict[str, Any]:
    results = root / "results"
    table = json.loads((results / "model_pass_table.json").read_text(encoding="utf-8"))
    sweep_path = sweep_for(results, table)
    sweep = json.loads(sweep_path.read_text(encoding="utf-8"))
    answers: list[dict[str, Any]] = sweep.get("answers", [])
    features = sorted({str(a.get("feature")) for a in answers})
    models = sorted({str(a.get("model")) for a in answers})
    return {
        "real": True,
        "synthetic": False,
        "script": "evals/model_card.py",
        "sweep": sweep_path.relative_to(root).as_posix(),
        "sweep_generated_at_utc": sweep.get("generated_at_utc"),
        "by_feature": {f: tally([a for a in answers if a.get("feature") == f]) for f in features},
        "by_model_and_feature": {
            m: {
                f: tally([a for a in answers if a.get("model") == m and a.get("feature") == f])
                for f in features
            }
            for m in models
        },
        "cost": cost(results / "cost_log.jsonl"),
        "benchmark": benchmark(root),
        "footage_kept": footage_kept(root),
    }


def dumps(doc: dict[str, Any]) -> str:
    return json.dumps(doc, indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if results/ is out of date")
    args = parser.parse_args(argv)
    try:
        text = dumps(build())
    except SweepNotFound as exc:
        print(f"model-card: {exc}")
        return 1
    if args.check:
        now = OUT.read_text(encoding="utf-8") if OUT.is_file() else ""
        if now != text:
            print("model-card: results/model_card.json is out of date; run evals/model_card.py")
            return 1
        print("model-card: results/model_card.json matches the sweep and the cost log")
        return 0
    OUT.write_text(text, encoding="utf-8")
    doc = json.loads(text)
    print(
        f"model-card: {doc['sweep']}, {doc['cost']['real_calls']} paid calls, "
        f"{doc['cost']['real_usd']} USD"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
