"""Cost per assessment and per 100 frames from results/cost_log.jsonl, for Update 16A section 4.

The log has one line per model call (evals/model_sweep.py, CostLog.append), and one call judges one
photo or one frame, so an assessment here is one call. Only lines with real true count: a fake run
costs nothing and says nothing about price. If there are no real lines the report says so and
gives no number, because a number made from fake lines would be a made-up number (hard rule 12).
Writes results/harden/costs.md and results/harden/costs.json.

  uv run python scripts/harden_costs.py
"""

from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FRAME_PURPOSES = {"footage", "frames", "video", "benchmark_frames", "walk"}


def load(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def summarize(rows: list[dict[str, Any]], log: str) -> dict[str, Any]:
    """Everything costs.json holds but its time stamp, from the log's lines."""
    real = [r for r in rows if r.get("real") is True]
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in real:
        groups[(str(r.get("purpose")), str(r.get("model")))].append(r)
    table = []
    for (purpose, model), got in sorted(groups.items()):
        cost = sum(float(r.get("cost_usd", 0)) for r in got)
        table.append(
            {
                "purpose": purpose,
                "model": model,
                "calls": len(got),
                "cost_usd": round(cost, 6),
                "per_assessment_usd": round(cost / len(got), 6),
                "per_100_usd": round(100 * cost / len(got), 4),
                "frames": purpose in FRAME_PURPOSES,
                "input_tokens": sum(int(r.get("input_tokens", 0)) for r in got),
                "output_tokens": sum(int(r.get("output_tokens", 0)) for r in got),
            }
        )
    fake_by_purpose: dict[str, int] = defaultdict(int)
    for r in rows:
        if r.get("real") is not True:
            fake_by_purpose[str(r.get("purpose"))] += 1
    return {
        "log": log,
        "lines": len(rows),
        "real_lines": len(real),
        "not_real_lines_by_purpose": dict(fake_by_purpose),
        "groups": table,
    }


def page(summary: dict[str, Any]) -> str:
    """costs.md, from costs.json alone, so the two cannot say different things."""
    table = summary["groups"]
    fake_by_purpose = summary["not_real_lines_by_purpose"]
    lines = [
        "# Cost per assessment",
        "",
        f"Computed {summary['checked_utc']} by `uv run python scripts/harden_costs.py` from "
        f"`{summary['log']}`. One line in the log is one model call, and one call judges one "
        "photo or one frame, so an assessment is one call. Only lines marked real count.",
        "",
        f"The log has {summary['lines']} lines and {summary['real_lines']} of them are real.",
        "",
    ]
    if not table:
        lines += [
            "No real lines, so there is no cost per assessment and no cost per 100 frames yet. "
            "No paid model run has been logged on this branch. The numbers arrive with the model "
            "run; run this script again after it.",
            "",
        ]
        if fake_by_purpose:
            parts = ", ".join(f"{n} from {p}" for p, n in sorted(fake_by_purpose.items()))
            lines += [
                f"The lines that are not real: {parts}. They cost 0 and say nothing about price. "
                "`evals/model_sweep.py` says fake runs write `results/cost_log_fake.jsonl`, so "
                "fake lines in the real log are worth a look.",
                "",
            ]
    else:
        lines += [
            "| Purpose | Model | Calls | Cost (USD) | Per assessment (USD) | Per 100 (USD) |",
            "|---|---|---|---|---|---|",
            *[
                f"| {g['purpose']} | {g['model']} | {g['calls']} | {g['cost_usd']} | "
                f"{g['per_assessment_usd']} | {g['per_100_usd']} |"
                for g in table
            ],
            "",
            "Per 100 is per 100 frames on the rows whose purpose is a footage run ("
            + ", ".join(sorted(FRAME_PURPOSES))
            + "), and per 100 photos on the others.",
            "",
        ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--log", type=Path, default=ROOT / "results" / "cost_log.jsonl")
    ap.add_argument("--out", type=Path, default=ROOT / "results" / "harden")
    args = ap.parse_args()
    rows = load(args.log)
    rel = args.log.relative_to(ROOT) if ROOT in args.log.resolve().parents else args.log
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    summary = {"checked_utc": stamp, **summarize(rows, str(rel))}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "costs.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    (args.out / "costs.md").write_text(page(summary), encoding="utf-8")
    print(f"{len(rows)} lines, {summary['real_lines']} real; wrote {args.out / 'costs.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
