"""Write what every paid run got back from the models to evals/fixtures/raw/ (UPDATE_29 section 4).

Run by hand once after a paid run: uv run python evals/extract_raw.py
make reproduce never runs this. It regrades every number from the files this wrote, and fails if a
committed number differs, so an edit to a results file cannot pass unnoticed.

One JSON Lines file per paid run in evals/paid_runs.py. The first line says what the file holds.
Then one line per reply, and one line per call from results/cost_log.jsonl with its token counts,
in the order the log has them. Nothing else: no key, no request, no image, no person. A reply is a
model's answer about a creek photo or a video frame.

What each kind of run kept, and so what its fixture can hold:

- model_sweep: every reply as the model sent it (the answer tool's input, or its text), its token
  counts and any error. Everything the pass table, the item accuracy and the cost come from.
- footage: every answer after evals/footage.py forced it (answer, note, malformed), because the
  run kept those and not the reply itself; and the calls, split into the frame pass and the
  adversarial pass. The adversarial pass kept only each model's majority answer per frame.
- benchmark: every reply, like a sweep, for a run made after this change. The two runs of Sep 24
  kept counts, not answers, so their fixtures hold the calls only: the right-answer counts of
  those runs cannot be regraded from a reply; make reproduce says so and regrades their
  accuracies, intervals and cost from what there is.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from evals.paid_runs import PAID_RUNS, PaidRun

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
RAW_DIR = ROOT / "evals" / "fixtures" / "raw"
COST_LOG = RESULTS / "cost_log.jsonl"
ADVERSARIAL_CALLS_PER_MODEL = 4 * 4  # frames in evals/fixtures x features, per run


def load_cost_log(path: Path = COST_LOG) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def run_window(run: PaidRun, runs: Sequence[PaidRun], results: Path) -> tuple[str, str]:
    """The cost log lines of a run: its purpose, after the previous run of that kind ended."""
    same = [r for r in runs if r.kind == run.kind]
    index = same.index(run)
    end = json.loads((results / run.results_name).read_text())["generated_at_utc"]
    start = ""
    if index:
        start = json.loads((results / same[index - 1].results_name).read_text())["generated_at_utc"]
    return start, end


def calls_of(
    run: PaidRun, log: Sequence[dict[str, Any]], runs: Sequence[PaidRun], results: Path
) -> list[tuple[int, dict[str, Any]]]:
    start, end = run_window(run, runs, results)
    return [
        (number, line)
        for number, line in enumerate(log, start=1)
        if line["purpose"] == run.kind and line["real"] and start < line["ts_utc"] <= end
    ]


def split_adversarial(calls: Sequence[tuple[int, dict[str, Any]]], runs_per_item: int) -> list[str]:
    """Which pass each footage call was in. A model's adversarial pass starts only after its frame
    pass has returned (evals/footage.py), so a model's last calls are its adversarial ones."""
    totals = Counter(line["model"] for _n, line in calls)
    per_model = ADVERSARIAL_CALLS_PER_MODEL * runs_per_item
    seen: Counter[str] = Counter()
    passes: list[str] = []
    for _n, line in calls:
        model = line["model"]
        passes.append("adversarial" if seen[model] >= totals[model] - per_model else "frames")
        seen[model] += 1
    return passes


def header(
    run: PaidRun, doc: dict[str, Any], calls: Sequence[tuple[int, dict[str, Any]]], kept: str
) -> dict[str, Any]:
    return {
        "fixture": "the raw model responses of one paid run, for make reproduce",
        "run": f"results/{run.results_name}",
        "script": "evals/assist_flags.py"
        if run.kind == "assist_answers"
        else f"evals/{run.kind}.py",
        "generated_at_utc": doc["generated_at_utc"],
        "billing": run.billing,
        "prices_per_million": {m: list(p) for m, p in run.prices.items()},
        "prices_from": run.prices_from,
        "cost_log": "results/cost_log.jsonl",
        "cost_log_lines": [calls[0][0], calls[-1][0]] if calls else None,
        "calls": len(calls),
        "kept": kept,
        "written_by": "evals/extract_raw.py",
    }


REPLIES_KEPT = "every reply: the answer tool's input as sent, tokens, error"


def reply_line(answer: dict[str, Any]) -> dict[str, Any]:
    """One reply of a sweep or a benchmark: what the model sent and what it cost in tokens."""
    return {
        "model": answer["model"],
        "item_id": answer["item_id"],
        "run": answer["run"],
        "raw": answer["raw"],
        "input_tokens": answer["input_tokens"],
        "output_tokens": answer["output_tokens"],
        "error": answer["error"],
    }


def call_line(number: int, line: dict[str, Any], pass_name: str | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "call": number,
        "model": line["model"],
        "input_tokens": line["input_tokens"],
        "output_tokens": line["output_tokens"],
    }
    if pass_name is not None:
        out["pass"] = pass_name
    return out


def fixture_lines(
    run: PaidRun, log: Sequence[dict[str, Any]], runs: Sequence[PaidRun], results: Path
) -> list[dict[str, Any]]:
    doc = json.loads((results / run.results_name).read_text(encoding="utf-8"))
    if doc.get("real") is not True:
        raise ValueError(f"{run.results_name} is not a paid run")
    calls = calls_of(run, log, runs, results)
    # assist_answers: part 2's eight items (evals/assist_flags.py --collect), kept like a sweep.
    if run.kind in ("model_sweep", "assist_answers") or (
        run.kind == "benchmark" and doc.get("answers")
    ):
        lines = [header(run, doc, calls, REPLIES_KEPT)]
        lines += [reply_line(a) for a in doc["answers"]]
        lines += [call_line(n, line) for n, line in calls]
        return lines
    if run.kind == "footage":
        passes = split_adversarial(calls, int(doc["runs"]))
        lines = [
            header(
                run,
                doc,
                calls,
                "every answer as the run kept it (after forcing), and every call with its pass",
            )
        ]
        lines += [
            {
                "model": a["model"],
                "frame": a["frame"],
                "feature": a["feature"],
                "run": a["run"],
                "answer": a["answer"],
                "note": a["note"],
                "malformed": a["malformed"],
            }
            for a in doc["answers"]
        ]
        lines += [call_line(n, line, p) for (n, line), p in zip(calls, passes, strict=True)]
        return lines
    if run.kind == "benchmark":
        lines = [
            header(
                run,
                doc,
                calls,
                "the calls only: this run kept counts, not answers, so no reply survives",
            )
        ]
        lines += [call_line(n, line) for n, line in calls]
        return lines
    raise ValueError(f"unknown kind {run.kind}")


def write_fixture(path: Path, lines: Sequence[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # ensure_ascii keeps any dash a model wrote as an escape, as results/ does (hard rule 18).
    text = "".join(json.dumps(line, sort_keys=True) + "\n" for line in lines)
    path.write_text(text, encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--results-dir", type=Path, default=RESULTS)
    parser.add_argument("--out", type=Path, default=RAW_DIR)
    args = parser.parse_args(argv)
    log = load_cost_log(args.results_dir / "cost_log.jsonl")
    for run in PAID_RUNS:
        lines = fixture_lines(run, log, PAID_RUNS, args.results_dir)
        write_fixture(args.out / run.fixture_name, lines)
        print(f"wrote {run.fixture_name}: {len(lines) - 1} lines after the header")
    return 0


if __name__ == "__main__":
    sys.exit(main())
