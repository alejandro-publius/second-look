"""The checker's flags for part 2, the assisted second look (UPDATE_31 section 2 item 2).

Two steps, so nothing ever calls a model while a person takes part 2:

1. --collect (paid): every configured model answers the eight part 2 items, the same question as
   part 1, three runs, through the same client as evals/model_sweep.py. Writes
   results/assist_answers_<stamp>.json with every raw answer and note, and logs each call in
   results/cost_log.jsonl. This is the models' stored answers.

2. The default step (free, pure): reads the newest real stored answers and the committed pass
   table, and writes results/assist_flags.json. For each item the checker model named in
   content/part2_items.yaml gets one flag or none:

   - its answer is the one given in at least 2 of the 3 runs; a cant_tell majority or no majority
     gives no flag;
   - the candidate flag goes through core.gate.parse_flags with the pass table, so a feature the
     model did not pass is dropped by the gate, with the gate's own reason written beside it;
   - a kept flag carries only the side it points at, present for yes and absent for no.

The web and the Worker read the flags from this file at build time, so every participant in the
assisted arm meets exactly the same flags. A flag never sets an answer: the person answers first,
a flag that disagrees makes one question appear, and the person's final choice is what is stored.

Run: uv run python evals/assist_flags.py --collect     (paid, needs ANTHROPIC_API_KEY in .env)
     uv run python evals/assist_flags.py               (build results/assist_flags.json)
     uv run python evals/assist_flags.py --check       (fail if the committed file is stale)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml

from core.gate import parse_flags
from evals import model_sweep as ms

ROOT = Path(__file__).resolve().parents[1]
ITEMS_YAML = ROOT / "content" / "part2_items.yaml"
RESULTS = ROOT / "results"
FLAGS_JSON = RESULTS / "assist_flags.json"
PASS_TABLE = RESULTS / "model_pass_table.json"
SCRIPT = "evals/assist_flags.py"
ANSWER_SIDE = {"yes": "present", "no": "absent"}
MAJORITY = 2  # of 3 runs, the same bar as the pass table's per-item rule


def load_items(root: Path = ROOT) -> tuple[list[ms.Item], str]:
    """The eight items as sweep Items, and the checker model id."""
    manifest = ms.load_manifest(root)
    doc = yaml.safe_load((root / "content" / "part2_items.yaml").read_text(encoding="utf-8"))
    items: list[ms.Item] = []
    for row in doc["items"]:
        photo = manifest[str(row["photo_id"])]
        if photo["role"] != "part2":
            raise ValueError(f"part 2 item {row['id']} uses a {photo['role']} photo")
        items.append(
            ms.Item(
                id=str(row["id"]),
                feature=str(row["feature"]),
                gold=str(row["gold"]),
                photo_id=str(row["photo_id"]),
                photo_path=root / "photos" / photo["file"],
                is_placeholder=photo["license"] == "placeholder",
            )
        )
    return items, str(doc["checker_model"])


def majority(answers: Sequence[str]) -> str | None:
    """The answer given in at least MAJORITY runs, or None."""
    if not answers:
        return None
    answer, n = Counter(answers).most_common(1)[0]
    return answer if n >= MAJORITY else None


def flag_for_item(
    item_id: str,
    feature: str,
    answers: Sequence[Mapping[str, Any]],
    *,
    model_id: str,
    pass_table: Mapping[str, Any],
) -> dict[str, Any]:
    """One item's flag entry. Pure. answers are the checker's stored answers for this item."""
    entry: dict[str, Any] = {"item_id": item_id, "feature": feature, "flag": None}
    said = [str(a.get("answer", "")) for a in answers]
    entry["model_answers"] = said
    top = majority(said)
    if top is None:
        entry["reason"] = "no answer in 2 of 3 runs"
        return entry
    if top not in ANSWER_SIDE:
        entry["reason"] = f"the model's answer was {top}"
        return entry
    note = next((str(a.get("note") or "") for a in answers if a.get("answer") == top), "")
    candidate = {
        "feature": feature,
        "confidence": round(said.count(top) / len(said), 4),
        "note": note.strip() or "no note",
    }
    flags, reasons = parse_flags(candidate, model_id=model_id, pass_table=pass_table)
    if not flags:
        entry["reason"] = "; ".join(reasons) or "dropped by the gate"
        return entry
    flag = flags[0]
    entry["flag"] = {
        "points_to": ANSWER_SIDE[top],
        "confidence": flag.confidence,
        "note": flag.note,
    }
    entry["reason"] = "kept by the gate"
    return entry


def build_flags(
    items: Sequence[ms.Item],
    answers_doc: Mapping[str, Any],
    pass_table: Mapping[str, Any],
    *,
    model_id: str,
    answers_file: str,
) -> dict[str, Any]:
    """The whole results/assist_flags.json document. Pure."""
    by_item: dict[str, list[Mapping[str, Any]]] = {}
    for a in answers_doc.get("answers", []):
        if a.get("model") == model_id:
            by_item.setdefault(str(a.get("item_id")), []).append(a)
    entries = [
        flag_for_item(
            i.id, i.feature, by_item.get(i.id, []), model_id=model_id, pass_table=pass_table
        )
        for i in items
    ]
    real = answers_doc.get("real") is True and pass_table.get("real") is True
    return {
        "script": SCRIPT,
        "real": real,
        "synthetic": not real,
        "checker_model": model_id,
        "answers_file": answers_file,
        "pass_table_generated_at_utc": pass_table.get("generated_at_utc"),
        "rule": (
            "one flag per item when the checker gave the same yes or no in 2 of 3 runs and the "
            "gate kept it, which it does only for a feature the checker passed"
        ),
        "items": entries,
        "n_flags": sum(1 for e in entries if e["flag"] is not None),
    }


def newest_answers(results: Path = RESULTS) -> Path | None:
    real = []
    for p in sorted(results.glob("assist_answers_*.json")):
        doc = json.loads(p.read_text(encoding="utf-8"))
        if doc.get("real") is True:
            real.append(p)
    return real[-1] if real else None


def render(doc: Mapping[str, Any]) -> str:
    return json.dumps(doc, indent=2, sort_keys=True) + "\n"


def build_from_disk(root: Path = ROOT) -> tuple[dict[str, Any] | None, str]:
    items, model_id = load_items(root)
    answers_path = newest_answers(root / "results")
    if answers_path is None:
        return None, "no real stored answers yet: run with --collect first"
    doc = build_flags(
        items,
        json.loads(answers_path.read_text(encoding="utf-8")),
        json.loads((root / "results" / "model_pass_table.json").read_text(encoding="utf-8")),
        model_id=model_id,
        answers_file=str(answers_path.relative_to(root)),
    )
    return doc, ""


def collect(args: argparse.Namespace, environ: Mapping[str, str]) -> int:
    config = ms.load_models_config()
    pricing = ms.load_pricing()
    model_ids = list(args.models) if args.models else config.model_ids()
    runs = config.settings.runs
    items, _ = load_items()
    questions = ms.load_questions()
    images = ms.prepared_images(items, config.settings)
    cost_log = ms.CostLog(RESULTS / "cost_log.jsonl")
    client, why_not = ms.build_real_client(
        model_ids=model_ids,
        config=config,
        pricing=pricing,
        cost_log=cost_log,
        env_file=ms.DEFAULT_ENV_FILE,
        environ=environ,
        purpose="assist_answers",
        poll_seconds=args.poll_seconds,
    )
    if client is None:
        print(why_not)
        return 2
    est = ms.estimate_cost(
        model_ids, images, pricing, config.settings, runs=runs, batch=not ms.sync_mode(environ)
    )
    print(
        f"real run: {len(model_ids)} models, {len(items)} part 2 items, {runs} runs; "
        f"expected about {est['expected_usd']:.2f} USD"
    )
    records = ms.run_sweep(
        client, model_ids, items, questions, runs=runs, settings=config.settings, images=images
    )
    doc = {
        "real": True,
        "synthetic": False,
        "generated_at_utc": ms.now_utc(),
        "script": SCRIPT,
        "runs": runs,
        "items": [i.id for i in items],
        "prompt_system": config.prompt.system,
        "prompt_user_template": config.prompt.user_template,
        "counts": {
            "answers": len(records),
            "malformed": sum(1 for r in records if r.malformed),
            "errors": sum(1 for r in records if r.error),
            "cost_usd": round(sum(r.cost_usd for r in records), 6),
        },
        "answers": [asdict(r) for r in records],
    }
    out = RESULTS / f"assist_answers_{ms.stamp()}.json"
    ms.write_json(out, doc)
    print(f"wrote {out.relative_to(ROOT)}: {len(records)} answers, {doc['counts']}")
    return 0


def main(argv: Sequence[str] | None = None, *, environ: Mapping[str, str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    p.add_argument("--collect", action="store_true", help="paid run of every model on 8 items")
    p.add_argument(
        "--check", action="store_true", help="fail if results/assist_flags.json is stale"
    )
    p.add_argument("--models", nargs="*", default=None)
    p.add_argument("--poll-seconds", type=float, default=30.0)
    args = p.parse_args(argv)
    if args.collect:
        return collect(args, environ if environ is not None else os.environ)
    doc, why = build_from_disk()
    if doc is None:
        print(f"assist-flags: {why}")
        return 2
    text = render(doc)
    if args.check:
        on_disk = FLAGS_JSON.read_text(encoding="utf-8") if FLAGS_JSON.exists() else ""
        if on_disk != text:
            print("assist-flags: results/assist_flags.json is stale, run evals/assist_flags.py")
            return 1
        print(f"assist-flags: up to date, {doc['n_flags']} flag(s) on 8 items")
        return 0
    FLAGS_JSON.write_text(text, encoding="utf-8")
    print(f"assist-flags: wrote {FLAGS_JSON.relative_to(ROOT)}, {doc['n_flags']} flag(s)")
    for e in doc["items"]:
        side = e["flag"]["points_to"] if e["flag"] else "none"
        print(f"  {e['item_id']} {e['feature']:16} flag {side:8} {e['reason']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
