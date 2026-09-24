"""The AI on frames from open creek footage (Update 14 section 3 item 6).

The pool is every manifest row with role benchmark that came from a video (scene_id video-*).
Every frame is asked all four feature questions, word for word from content/features.yaml, by
every configured model, three runs each, through the same client as the 16-photo test.

What it reports, per feature:

- accuracy against the description label, with a Wilson 95 percent interval, on the frames whose
  video description supports a label for that feature. None may exist; the count says so.
- agreement between models on the unlabelled frames: for each pair of models, the share of
  frames where their majority answers match, and Cohen's kappa. Agreement is not accuracy: two
  models can agree and both be wrong. docs/REAL_VS_SYNTHETIC.md says so.
- what the gate did: every yes becomes a candidate flag and goes through core/gate.py with the
  committed pass table. Kept flags and drop reasons are counted. A pass table from the fake client
  licenses nothing, so on a fake run every candidate is dropped, which is the rule working.
- the adversarial frames (blank, black, indoor, a screenshot of text): what each model says.
- the ablation on labelled frames, only when labelled frames exist.
- cost, and cost per 100 frames.

Run: uv run python evals/footage.py --fake     fake client, spends nothing, stamped SYNTHETIC
     uv run python evals/footage.py --real     Batch API, needs ANTHROPIC_API_KEY in .env

The real run is capped at --max-usd (25 by default, Update 14). Models run cheapest first. Before
each model the expected cost of that model, its footage frames and its adversarial frames
together, is checked against what is left of the cap, using the spend actually measured so far,
and the model is skipped rather than pass it. A model's adversarial pass runs right after its
footage frames, so its measured cost counts before the next model's check.

Writes results/footage_<stamp>.json and results/footage_latest.json.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from itertools import combinations
from pathlib import Path
from typing import Any

from core.gate import parse_flags
from core.records import FEATURES
from evals.agreement import cohens_kappa
from evals.benchmark import accuracy_cell
from evals.fixtures import adversarial_frames
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
    Query,
    build_real_client,
    estimate_cost,
    load_manifest,
    load_models_config,
    load_pricing,
    load_questions,
    now_utc,
    prepared_images,
    record_from,
    stamp,
    sync_mode,
    write_json,
)

SCRIPT = "evals/footage.py"
DEFAULT_CAP_USD = 25.0
PASS_TABLE = DEFAULT_RESULTS / "model_pass_table.json"


def frame_items(manifest: Mapping[str, Mapping[str, str]], root: Path = ROOT) -> list[Item]:
    """One item per frame and feature. The gold is the description label, or empty."""
    items: list[Item] = []
    for row_id, row in sorted(manifest.items()):
        if row.get("role") != "benchmark" or not row.get("scene_id", "").startswith("video-"):
            continue
        path = root / "photos" / row["file"]
        for feature in FEATURES:
            gold = row.get("gold_label", "") if row.get("feature") == feature else ""
            items.append(
                Item(
                    id=f"{row_id}|{feature}",
                    feature=feature,
                    gold=gold if gold in ("present", "absent") else "",
                    photo_id=row_id,
                    photo_path=path,
                    is_placeholder=False,
                )
            )
    return items


def majority(answers: Sequence[str]) -> str:
    """The most common answer over the runs; a tie reads as cant_tell."""
    if not answers:
        return "cant_tell"
    counts = Counter(answers).most_common()
    if len(counts) > 1 and counts[0][1] == counts[1][1]:
        return "cant_tell"
    return counts[0][0]


def labelled_accuracy(
    records: Sequence[AnswerRecord], model_ids: Sequence[str]
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for model_id in model_ids:
        cells: dict[str, Any] = {}
        for feature in FEATURES:
            rows = [r for r in records if r.model == model_id and r.feature == feature and r.gold]
            cells[feature] = accuracy_cell(sum(r.correct for r in rows), len(rows))
        out[model_id] = cells
    return out


def model_agreement(
    records: Sequence[AnswerRecord], model_ids: Sequence[str]
) -> dict[str, dict[str, Any]]:
    """Per feature, per pair of models, on unlabelled frames: share agreeing and kappa."""
    per: dict[tuple[str, str, str], list[str]] = {}
    for r in records:
        if r.gold:
            continue
        frame = r.item_id.split("|", 1)[0]
        per.setdefault((r.model, frame, r.feature), []).append(r.answer)
    out: dict[str, dict[str, Any]] = {}
    for feature in FEATURES:
        frames = sorted({f for (_m, f, feat) in per if feat == feature})
        pairs: dict[str, Any] = {}
        for a, b in combinations(model_ids, 2):
            xs = [majority(per.get((a, f, feature), [])) for f in frames]
            ys = [majority(per.get((b, f, feature), [])) for f in frames]
            n = len(frames)
            agree = sum(1 for x, y in zip(xs, ys, strict=True) if x == y)
            kappa = cohens_kappa(xs, ys) if n else None
            pairs[f"{a} vs {b}"] = {
                "frames": n,
                "agree": agree,
                "share": round(agree / n, 4) if n else None,
                "kappa": round(kappa, 4) if kappa is not None else None,
            }
        yes_share = {
            m: (
                round(
                    sum(1 for f in frames if majority(per.get((m, f, feature), [])) == "yes")
                    / len(frames),
                    4,
                )
                if frames
                else None
            )
            for m in model_ids
        }
        out[feature] = {"frames": len(frames), "pairs": pairs, "yes_share": yes_share}
    return out


def candidate_flag(feature: str, note: str) -> dict[str, Any]:
    """The candidate flag a yes answer becomes before the gate sees it.

    A forced answer carries no confidence, so every candidate gets 1.0. evals/footage_example.py
    builds its two candidates with this same function, so the example and the run cannot differ.
    """
    return {"feature": feature, "confidence": 1.0, "note": note or "no note"}


def gate_outcome(records: Sequence[AnswerRecord], pass_table: Mapping[str, Any]) -> dict[str, Any]:
    """Every yes becomes a candidate flag and goes through the real gate, with the real table."""
    kept = 0
    drops: Counter[str] = Counter()
    not_candidates: Counter[str] = Counter()
    for r in records:
        if r.malformed:
            not_candidates["malformed answer, forced to cant_tell"] += 1
            continue
        if r.answer != "yes":
            not_candidates[f"answered {r.answer}, so no flag is proposed"] += 1
            continue
        candidate = candidate_flag(r.feature, r.note)
        flags, reasons = parse_flags(candidate, model_id=r.model, pass_table=pass_table)
        kept += len(flags)
        for reason in reasons:
            # "flag 1: feature pipe_running not passed by model x" -> the part after the colon
            drops[reason.split(": ", 1)[-1]] += 1
    return {
        "pass_table_real": pass_table.get("real") is True,
        "candidates": kept + sum(drops.values()),
        "kept": kept,
        "dropped": sum(drops.values()),
        "drop_reasons": dict(drops.most_common()),
        "not_candidates": dict(not_candidates.most_common()),
    }


def adversarial_images() -> dict[str, bytes]:
    """One image per adversarial query and run, keyed like the queries, for the cost estimate."""
    return {
        f"adv-{name}|{feature}": data
        for name, data in adversarial_frames().items()
        for feature in FEATURES
    }


def adversarial(
    client: Client, model_ids: Sequence[str], questions: Mapping[str, str], runs: int
) -> tuple[dict[str, dict[str, dict[str, str]]], list[AnswerRecord]]:
    """Each adversarial frame, each feature, each model: the majority answer over the runs.

    The records come back too, so the caller can add what the pass cost to the spend.
    """
    frames = adversarial_frames()
    out: dict[str, dict[str, dict[str, str]]] = {}
    records: list[AnswerRecord] = []
    for model_id in model_ids:
        queries = [
            Query(
                custom_id=f"{model_id}|adv-{name}|{feature}|r{run}",
                item_id=f"adv-{name}|{feature}",
                feature=feature,
                question=questions[feature],
                image_bytes=data,
                model_id=model_id,
                run=run,
            )
            for run in range(runs)
            for name, data in frames.items()
            for feature in FEATURES
        ]
        raws = client.answer_many(queries)
        answers: dict[tuple[str, str], list[str]] = {}
        for q, raw in zip(queries, raws, strict=True):
            record = record_from(q, raw, "")
            records.append(record)
            name = q.item_id.split("|", 1)[0].removeprefix("adv-")
            answers.setdefault((name, q.feature), []).append(record.answer)
        for (name, feature), got in answers.items():
            out.setdefault(name, {}).setdefault(feature, {})[model_id] = majority(got)
    return out, records


def summary_lines(doc: Mapping[str, Any]) -> list[str]:
    tag = "REAL" if doc["real"] else "SYNTHETIC (fake client, no model was called)"
    lines = [
        f"footage: {tag}",
        f"frames {doc['pool']['frames']} from {doc['pool']['videos']} videos in "
        f"{doc['pool']['countries']} countries; "
        f"labelled frame answers {doc['pool']['labelled_items']}",
    ]
    for feature, cell in doc["agreement"].items():
        shares = [p["share"] for p in cell["pairs"].values() if p["share"] is not None]
        low = min(shares) if shares else None
        lines.append(
            f"  {feature}: {cell['frames']} unlabelled frames, lowest pairwise agreement "
            f"{low if low is not None else 'n/a'}"
        )
    g = doc["gate"]
    lines.append(
        f"gate: {g['candidates']} candidate flags, {g['kept']} kept, {g['dropped']} dropped "
        f"(pass table real: {g['pass_table_real']})"
    )
    lines.append(
        f"cost {doc['cost']['usd']:.4f} USD, per 100 frames {doc['cost']['per_100_frames_usd']}"
    )
    return lines


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--fake", action="store_true", help="fake client, spends nothing")
    mode.add_argument("--real", action="store_true", help="paid Batch API run")
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--runs", type=int, default=None, help="default from evals/models.yaml")
    p.add_argument("--models", nargs="*", default=None)
    p.add_argument("--max-usd", type=float, default=DEFAULT_CAP_USD)
    p.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS)
    p.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    p.add_argument("--poll-seconds", type=float, default=30.0)
    return p.parse_args(argv)


def main(argv: Sequence[str] | None = None, *, environ: Mapping[str, str] | None = None) -> int:
    import json

    args = parse_args(argv)
    env = environ if environ is not None else os.environ
    config = load_models_config()
    pricing = load_pricing()
    model_ids = list(args.models) if args.models else config.model_ids()
    runs = args.runs or config.settings.runs
    manifest = load_manifest()
    items = frame_items(manifest)
    if not items:
        print("footage: no benchmark frames in photos/manifest.csv; run scripts/make_frames.py")
        return 2
    questions = load_questions()
    images = prepared_images(items, config.settings)
    log_name = "cost_log.jsonl" if args.real else "cost_log_fake.jsonl"
    cost_log = CostLog(args.results_dir / log_name)
    one_per_frame = {i.photo_id: images[i.id] for i in items}

    client: Client
    if args.real:
        real_client, why_not = build_real_client(
            model_ids=model_ids,
            config=config,
            pricing=pricing,
            cost_log=cost_log,
            env_file=args.env_file,
            environ=env,
            purpose="footage",
            poll_seconds=args.poll_seconds,
        )
        if real_client is None:
            print(why_not)
            return 2
        client = real_client
    else:
        client = FakeClient(
            seed=args.seed,
            profiles=config.fake_profiles,
            items=items,
            cost_log=cost_log,
            purpose="footage",
        )

    # The adversarial pass is paid for like the footage frames, so the cap counts it too. Direct
    # calls (EVALS_SYNC=1) cost the full price, so the estimate uses it.
    batched = not (args.real and sync_mode(env))
    per_model = {
        m: estimate_cost([m], images, pricing, config.settings, runs=runs, batch=batched)[
            "expected_usd"
        ]
        for m in model_ids
    }
    adv_images = adversarial_images()
    adv_per_model = {
        m: estimate_cost([m], adv_images, pricing, config.settings, runs=runs, batch=batched)[
            "expected_usd"
        ]
        for m in model_ids
    }
    # Cheapest first, so a cap that bites stops the dearest model, not the cheapest.
    order = sorted(model_ids, key=lambda m: per_model[m] + adv_per_model[m])
    records: list[AnswerRecord] = []
    adv_out: dict[str, dict[str, dict[str, str]]] = {}
    spent = 0.0
    adv_spent = 0.0
    skipped: dict[str, str] = {}
    for model_id in order:
        expected = per_model[model_id] + adv_per_model[model_id]
        if args.real and spent + expected > args.max_usd:
            skipped[model_id] = (
                f"expected {expected:.2f} USD ({per_model[model_id]:.2f} on the footage frames, "
                f"{adv_per_model[model_id]:.2f} on the adversarial frames) with {spent:.2f} "
                f"spent would pass the {args.max_usd:.2f} USD cap"
            )
            continue
        queries = [
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
        raws = client.answer_many(queries)
        gold = {i.id: i.gold for i in items}
        mine = [record_from(q, r, gold[q.item_id]) for q, r in zip(queries, raws, strict=True)]
        records.extend(mine)
        spent += sum(r.cost_usd for r in mine)
        # Right after the model's own frames, so the next model's check sees what this cost.
        answered, adv_records = adversarial(client, [model_id], questions, runs)
        for name, by_feature in answered.items():
            for feature, by_model in by_feature.items():
                adv_out.setdefault(name, {}).setdefault(feature, {}).update(by_model)
        adv_cost = sum(r.cost_usd for r in adv_records)
        adv_spent += adv_cost
        spent += adv_cost
    ran = [m for m in order if m not in skipped]

    pass_table = json.loads(PASS_TABLE.read_text(encoding="utf-8")) if PASS_TABLE.exists() else {}
    videos = {manifest[i.photo_id]["scene_id"] for i in items}
    countries = {manifest[i.photo_id].get("coarse_location", "") for i in items} - {""}
    frames = len(one_per_frame)
    doc: dict[str, Any] = {
        "real": bool(args.real),
        "synthetic": not args.real,
        "generated_at_utc": now_utc(),
        "script": SCRIPT,
        "seed": None if args.real else args.seed,
        "runs": runs,
        "models": ran,
        "models_skipped_for_cap": skipped,
        "pool": {
            "frames": frames,
            "videos": len(videos),
            "countries": len(countries),
            "country_names": sorted(countries),
            "labelled_items": sum(1 for i in items if i.gold),
            "labelled_frames": len({i.photo_id for i in items if i.gold}),
        },
        "accuracy_against_description_labels": labelled_accuracy(records, ran),
        "agreement": model_agreement(records, ran),
        "gate": gate_outcome(records, pass_table),
        "adversarial": adv_out,
        "ablation": (
            "not run: no frame carries a description label, so there is nothing to score it on"
            if not any(i.gold for i in items)
            else "run evals/ablation.py on the labelled frames"
        ),
        # Every answer, so scripts/build_walks.py can gate the flags for a clip's own frames.
        "answers": [
            {
                "model": r.model,
                "frame": r.item_id.split("|", 1)[0],
                "feature": r.feature,
                "run": r.run,
                "answer": r.answer,
                "note": r.note,
                "malformed": r.malformed,
            }
            for r in records
        ],
        "notes_sample": [
            {"model": r.model, "frame": r.item_id, "answer": r.answer, "note": r.note}
            for r in records
            if r.note and r.answer == "yes"
        ][:30],
        # Everything paid for, the adversarial pass included.
        "cost": {
            "usd": round(spent, 6),
            "adversarial_usd": round(adv_spent, 6),
            "per_100_frames_usd": round(spent / frames * 100, 4) if frames else None,
            "expected_real_usd_by_model": per_model,
            "expected_adversarial_usd_by_model": adv_per_model,
        },
    }
    if not args.real:
        doc["stamp"] = "SYNTHETIC"
    path = args.results_dir / f"footage_{stamp()}.json"
    write_json(path, doc)
    write_json(args.results_dir / "footage_latest.json", doc)
    print("\n".join(summary_lines(doc)))
    print(f"wrote {path.name} and footage_latest.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
