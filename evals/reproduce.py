"""make reproduce: the AI numbers in results/, graded again from raw replies and seeds.

No network and no key. Every socket to another machine is refused, and the run fails if one was
tried. It reads only what is committed:

- the raw replies of every paid run in evals/fixtures/raw/ (evals/extract_raw.py wrote them once),
- the price each run was billed at and how (evals/paid_runs.py),
- the test key, the questions and the photo manifest in content/ and photos/,
- the seeds in the synthetic results and the fake profiles in evals/fixtures/seeds.json,

and runs the same code the runs ran: core.checker forces each reply, core.gate decides each flag,
and evals/ builds each table. Then it compares every number, every true or false and every answer
in the committed results file with the regraded one, and fails if any differs.

Paid runs (evals/paid_runs.py): the three sweeps of the 16 photos, and with them
results/model_pass_table.json and results/model_item_accuracy.json; the two footage runs and
results/footage_latest.json; the two benchmark runs; and every line of results/cost_log.jsonl.
Synthetic runs: the three fake sweeps, the two fake benchmarks, the fake footage run, the
synthetic usability analysis, the three examples, the power simulation and the consensus
coarseness simulation.

Some numbers cannot be regraded, because the run never kept what they came from. They are named
in the output with the reason, never skipped in silence:

- the right-answer counts of the two paid benchmark runs: evals/benchmark.py kept counts, not
  answers, until this change. Their accuracies, intervals and cost are regraded;
- the adversarial answers of the footage runs: only each model's majority answer was kept;
- results/ablation_20260921T001415Z.json: its rule stub is keyed to the bytes of gray placeholder
  images the repository no longer has;
- results/consensus_synthetic.json: made by an earlier rule of evals/consensus.py that was dropped
  as biased (docs/DECISIONS.md, 2026-09-23), so today's script makes a different file;
- results/agreement_20260921T001415Z.json: no model and no seed, it counts label columns of a
  manifest with placeholders the repository no longer has.

The other files in results/ are measurements of the build, not of a model: test counts, screens,
the FHIR validator's run, the footage pool, the API inventory. make check and verify-claims check
those.

Run: uv run python evals/reproduce.py        (make reproduce)
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import re
import sys
import tempfile
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
KEY_NAMES = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")

# ---------------------------------------------------------------------------------------------
# Comparing a committed file with its regraded twin


def leaves(doc: object, prefix: str = "") -> Iterator[tuple[str, object]]:
    """Every value in a JSON document with its JSON pointer."""
    if isinstance(doc, Mapping):
        for key, value in doc.items():
            yield from leaves(value, f"{prefix}/{key}")
    elif isinstance(doc, list):
        for index, value in enumerate(doc):
            yield from leaves(value, f"{prefix}/{index}")
    else:
        yield prefix, doc


def as_written(doc: object) -> object:
    """The document as write_json would put it on disk and json.load read it back."""
    return json.loads(json.dumps(doc, sort_keys=True))


def is_graded(value: object) -> bool:
    """A number, or a true or false such as a pass: what the count of regraded values counts."""
    return isinstance(value, int | float)


@dataclass
class Check:
    """One results file against what the raw replies or the seed give today."""

    path: str
    source: str
    values: int = 0
    problems: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    # A line of its own in place of "n values regraded", for a check that regrades nothing.
    summary: str | None = None
    regraded: bool = True

    def compare(self, committed: object, regraded: object, *, skip: Sequence[str] = ()) -> None:
        """Every value of the committed document must be in the regraded one, at the same place,
        of the same type and equal, and every regraded value must be in the committed one: a
        number deleted from a results file is a number that differs. Pointers matching a skip
        pattern are left out: timestamps and the paths of this machine, never a number."""
        mine = dict(leaves(as_written(regraded)))
        patterns = [re.compile(s) for s in skip]
        seen: set[str] = set()
        for pointer, value in leaves(committed):
            if any(p.fullmatch(pointer) for p in patterns):
                continue
            seen.add(pointer)
            if is_graded(value):
                self.values += 1
            if pointer not in mine:
                self.problems.append(f"{pointer}: committed {value!r}, regraded has nothing there")
                continue
            got = mine[pointer]
            if type(got) is not type(value) or got != value:
                self.problems.append(f"{pointer}: committed {value!r}, regraded {got!r}")
        for pointer, got in mine.items():
            if pointer in seen or any(p.fullmatch(pointer) for p in patterns):
                continue
            self.problems.append(f"{pointer}: regraded {got!r}, committed has nothing there")

    def expect(self, what: str, committed: object, regraded: object) -> None:
        if is_graded(committed):
            self.values += 1
        if as_written(committed) != as_written(regraded):
            self.problems.append(f"{what}: committed {committed!r}, regraded {regraded!r}")


STAMP_ONLY = (r"/generated_at_utc",)


def load(rel: str, root: Path) -> Any:
    return json.loads((root / rel).read_text(encoding="utf-8"))


def read_fixture(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    lines = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    if not lines:
        raise ValueError(f"{path} is empty")
    return lines[0], lines[1:]


# ---------------------------------------------------------------------------------------------
# Paid runs


def gold_key(root: Path) -> dict[str, tuple[str, str]]:
    """The frozen test key: item id to (feature, gold), from content/test_items.yaml."""
    from evals.common import load_test_items

    items = load_test_items(root / "content" / "test_items.yaml")
    return {str(r["id"]): (str(r["feature"]), str(r["gold"])) for r in items}


def check_key_frozen(root: Path) -> Check:
    """The key the sweeps are graded against is the one frozen before the first participant."""
    from scripts.freeze_key import key_hash, load_items

    check = Check("results/key_hash.json", "content/test_items.yaml")
    items = load_items(root)
    frozen = load("results/key_hash.json", root)
    check.expect("/key_sha256", frozen["key_sha256"], key_hash(items))
    check.expect("/n_items", frozen["n_items"], len(items))
    return check


def sweep_records(fixture: Path, run: Any, key: Mapping[str, tuple[str, str]]) -> list[Any]:
    """Every answer of a sweep or a benchmark, forced, graded and priced again from the raw reply.

    key maps each item the run asked about to its feature and its gold label."""
    from evals.model_sweep import Query, RawAnswer, record_from

    _head, lines = read_fixture(fixture)
    pricing = run.pricing()
    records = []
    for line in lines:
        if "item_id" not in line:
            continue
        feature, gold = key[line["item_id"]]
        query = Query(
            custom_id=f"{line['model']}|{line['item_id']}|r{line['run']}",
            item_id=line["item_id"],
            feature=feature,
            question="",
            image_bytes=b"",
            model_id=line["model"],
            run=int(line["run"]),
        )
        cost = (
            pricing.cost_usd(
                line["model"], line["input_tokens"], line["output_tokens"], batch=run.batch
            )
            if line["error"] is None
            else 0.0
        )
        raw = RawAnswer(
            payload=line["raw"],
            model_id=line["model"],
            input_tokens=int(line["input_tokens"]),
            output_tokens=int(line["output_tokens"]),
            cost_usd=cost,
            error=line["error"],
        )
        records.append(record_from(query, raw, gold))
    return records


def sweep_counts(records: Sequence[Any]) -> dict[str, Any]:
    return {
        "answers": len(records),
        "malformed": sum(1 for r in records if r.malformed),
        "errors": sum(1 for r in records if r.error),
        "cant_tell": sum(1 for r in records if r.answer == "cant_tell"),
        "cost_usd": round(sum(r.cost_usd for r in records), 6),
    }


def fixture_calls(fixture: Path) -> list[dict[str, Any]]:
    return [line for line in read_fixture(fixture)[1] if "call" in line]


def check_calls(
    check: Check, run: Any, calls: Sequence[dict[str, Any]], log: Sequence[dict[str, Any]]
) -> dict[int, float]:
    """Each call of the run is its line in the cost log, and that line's cost is its tokens at the
    run's price. Returns the regraded cost of each call by its line number."""
    pricing = run.pricing()
    costs: dict[int, float] = {}
    for call in calls:
        number = int(call["call"])
        line = log[number - 1] if 0 < number <= len(log) else None
        if line is None:
            check.problems.append(f"call {number} is not a line of results/cost_log.jsonl")
            continue
        for key in ("model", "input_tokens", "output_tokens"):
            if line[key] != call[key]:
                check.problems.append(
                    f"cost log line {number}: {key} {line[key]!r}, the raw reply says {call[key]!r}"
                )
        if line["purpose"] != run.kind or line["real"] is not True:
            check.problems.append(f"cost log line {number} is not a paid {run.kind} call")
        cost = pricing.cost_usd(
            call["model"], call["input_tokens"], call["output_tokens"], batch=run.batch
        )
        costs[number] = cost
        check.expect(f"cost log line {number} cost_usd", line["cost_usd"], cost)
    return costs


def check_sweep(run: Any, root: Path, log: Sequence[dict[str, Any]]) -> tuple[Check, list[Any]]:
    fixture = root / "evals" / "fixtures" / "raw" / run.fixture_name
    check = Check(f"results/{run.results_name}", f"evals/fixtures/raw/{run.fixture_name}")
    doc = load(f"results/{run.results_name}", root)
    records = sweep_records(fixture, run, gold_key(root))
    check.compare(doc["answers"], [asdict(r) for r in records])
    check.compare(doc["counts"], sweep_counts(records))
    check_calls(check, run, fixture_calls(fixture), log)
    return check, records


def check_pass_table(sweeps: Mapping[str, tuple[Any, list[Any]]], root: Path) -> list[Check]:
    """The committed pass table and item accuracy are the latest paid sweep's, graded again."""
    from evals.model_sweep import item_accuracy, load_test_items, pass_table

    table_doc = load("results/model_pass_table.json", root)
    acc_doc = load("results/model_item_accuracy.json", root)
    made_at = table_doc.get("generated_at_utc")
    source = next(
        (
            (run, records)
            for run, records in sweeps.values()
            if load(f"results/{run.results_name}", root)["generated_at_utc"] == made_at
        ),
        None,
    )
    table_check = Check("results/model_pass_table.json", "the paid sweep that wrote it")
    acc_check = Check("results/model_item_accuracy.json", "the paid sweep that wrote it")
    if source is None:
        table_check.problems.append(f"no paid sweep has the table's time {made_at}")
        return [table_check, acc_check]
    run, records = source
    table_check.source = acc_check.source = f"evals/fixtures/raw/{run.fixture_name}"
    models = list(dict.fromkeys(r.model for r in records))
    items = load_test_items(root)
    runs = 1 + max(r.run for r in records)
    table_check.compare(
        table_doc, pass_table(records, models, items, runs=runs, real=True), skip=STAMP_ONLY
    )
    acc_check.compare(acc_doc, item_accuracy(records, models, items, real=True), skip=STAMP_ONLY)
    return [table_check, acc_check]


def pass_table_of(records: Sequence[Any], root: Path) -> dict[str, Any]:
    from evals.model_sweep import load_test_items, pass_table

    models = list(dict.fromkeys(r.model for r in records))
    runs = 1 + max(r.run for r in records)
    return pass_table(records, models, load_test_items(root), runs=runs, real=True)


def footage_records(lines: Sequence[dict[str, Any]]) -> list[Any]:
    """The answers of a footage run as AnswerRecords, the way evals/footage.py held them."""
    from evals.model_sweep import AnswerRecord

    return [
        AnswerRecord(
            model=a["model"],
            item_id=f"{a['frame']}|{a['feature']}",
            feature=a["feature"],
            gold="",
            run=int(a["run"]),
            custom_id=f"{a['model']}|{a['frame']}|{a['feature']}|r{a['run']}",
            answer=a["answer"],
            note=a["note"],
            correct=False,
            malformed=bool(a["malformed"]),
            reason="",
            input_tokens=0,
            output_tokens=0,
            cost_usd=0.0,
            error=None,
            raw=None,
        )
        for a in lines
        if "frame" in a
    ]


def footage_numbers(
    doc: Mapping[str, Any],
    records: Sequence[Any],
    table: Mapping[str, Any],
    root: Path,
) -> dict[str, Any]:
    """Everything evals/footage.py computes from its answers, with the pass table it read."""
    from evals.footage import gate_outcome, labelled_accuracy, model_agreement

    models = list(doc["models"])
    return {
        "accuracy_against_description_labels": labelled_accuracy(records, models),
        "agreement": model_agreement(records, models),
        "gate": gate_outcome(records, table),
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
        "pool": footage_pool(root),
    }


def footage_pool(root: Path) -> dict[str, Any]:
    from evals.footage import frame_items
    from evals.model_sweep import load_manifest

    manifest = load_manifest(root)
    items = frame_items(manifest, root)
    countries = {manifest[i.photo_id].get("coarse_location", "") for i in items} - {""}
    return {
        "frames": len({i.photo_id for i in items}),
        "videos": len({manifest[i.photo_id]["scene_id"] for i in items}),
        "countries": len(countries),
        "country_names": sorted(countries),
        "labelled_items": sum(1 for i in items if i.gold),
        "labelled_frames": len({i.photo_id for i in items if i.gold}),
    }


def expected_costs(
    models: Sequence[str], prices: Any, runs: int, batch: bool, root: Path
) -> dict[str, dict[str, float]]:
    """The estimates evals/footage.py printed before it spent anything, from the frames' sizes."""
    from evals.footage import adversarial_images, frame_items
    from evals.model_sweep import (
        estimate_cost,
        load_manifest,
        load_models_config,
        prepared_images,
    )

    settings = load_models_config(root / "evals" / "models.yaml").settings
    items = frame_items(load_manifest(root), root)
    images = prepared_images(items, settings)
    adv = adversarial_images()
    return {
        "expected_real_usd_by_model": {
            m: estimate_cost([m], images, prices, settings, runs=runs, batch=batch)["expected_usd"]
            for m in models
        },
        "expected_adversarial_usd_by_model": {
            m: estimate_cost([m], adv, prices, settings, runs=runs, batch=batch)["expected_usd"]
            for m in models
        },
    }


def check_footage(
    run: Any,
    root: Path,
    log: Sequence[dict[str, Any]],
    table: Mapping[str, Any],
) -> Check:
    fixture = root / "evals" / "fixtures" / "raw" / run.fixture_name
    check = Check(f"results/{run.results_name}", f"evals/fixtures/raw/{run.fixture_name}")
    doc = load(f"results/{run.results_name}", root)
    _head, lines = read_fixture(fixture)
    records = footage_records(lines)
    regraded = footage_numbers(doc, records, table, root)
    for key, value in regraded.items():
        check.compare({key: doc[key]}, {key: value})
    # What the run paid: every call at the run's price, the frame pass and the adversarial pass,
    # summed model by model in the order the models ran, as evals/footage.py summed them.
    calls = fixture_calls(fixture)
    costs = check_calls(check, run, calls, log)
    spent = adv_spent = 0.0
    for model in doc["models"]:
        mine = [c for c in calls if c["model"] == model]
        spent += sum(costs[c["call"]] for c in mine if c["pass"] == "frames")
        adv = sum(costs[c["call"]] for c in mine if c["pass"] == "adversarial")
        adv_spent += adv
        spent += adv
    frames = regraded["pool"]["frames"]
    check.compare(
        doc["cost"],
        {
            "usd": round(spent, 6),
            "adversarial_usd": round(adv_spent, 6),
            "per_100_frames_usd": round(spent / frames * 100, 4) if frames else None,
            **expected_costs(doc["models"], run.pricing(), int(doc["runs"]), run.batch, root),
        },
    )
    adversarial_calls = sum(1 for c in calls if c["pass"] == "adversarial")
    check.notes.append(
        f"the run kept only each model's majority answer on the adversarial frames, so those "
        f"answers are as recorded; the cost of their {adversarial_calls} calls is regraded"
    )
    return check


def check_footage_latest(root: Path) -> Check:
    check = Check("results/footage_latest.json", "the newest footage run")
    newest = sorted((root / "results").glob("footage_2*.json"))[-1]
    check.compare(load("results/footage_latest.json", root), load(f"results/{newest.name}", root))
    check.source = f"results/{newest.name}"
    return check


def check_benchmark(run: Any, root: Path, log: Sequence[dict[str, Any]]) -> Check:
    from core.records import FEATURES
    from evals.benchmark import (
        accuracy_cell,
        labelled_pool,
        per_feature_accuracy,
        skipped_rows,
    )
    from evals.benchmark import unlabelled_video_frames as video_frames
    from evals.model_sweep import load_manifest

    fixture = root / "evals" / "fixtures" / "raw" / run.fixture_name
    check = Check(f"results/{run.results_name}", f"evals/fixtures/raw/{run.fixture_name}")
    doc = load(f"results/{run.results_name}", root)
    calls = fixture_calls(fixture)
    costs = check_calls(check, run, calls, log)
    check.expect("/cost_usd", doc["cost_usd"], round(sum(costs.values()), 6))
    manifest = load_manifest(root)
    pool = labelled_pool(manifest, root)
    check.compare(
        doc["pool"],
        {
            "n_photos": len(pool),
            "n_placeholders": sum(1 for i in pool if i.is_placeholder),
            "skipped_unlabelled": skipped_rows(manifest),
            "unlabelled_video_frames_left_to_evals_footage": video_frames(manifest),
            "by_feature": {f: sum(1 for i in pool if i.feature == f) for f in FEATURES},
            "photo_ids": [i.id for i in pool],
        },
    )
    if any("item_id" in line for line in read_fixture(fixture)[1]):
        # A run that kept its answers: grade every one again from its reply.
        key = {i.id: (i.feature, i.gold) for i in pool}
        records = sweep_records(fixture, run, key)
        check.compare(doc["answers"], [asdict(r) for r in records])
        check.compare(doc["models"], per_feature_accuracy(records, list(doc["models"])))
        return check
    runs = int(doc["runs"])
    # Every model that was called has its cells, no other model does, and each has the cells
    # evals/benchmark.py writes, so a model or a cell cut from the file is caught too.
    check.expect(
        "/models (the models with calls in the cost log)",
        sorted(doc["models"]),
        sorted({c["model"] for c in calls}),
    )
    shape = sorted(per_feature_accuracy([], ["any"])["any"])
    for model, cells in doc["models"].items():
        check.expect(f"/models/{model} (its cells)", sorted(cells), shape)
        n_calls = sum(1 for c in calls if c["model"] == model)
        check.expect(f"/models/{model}/all/n (calls in the cost log)", cells["all"]["n"], n_calls)
        total_right = 0
        for feature in FEATURES:
            cell = cells[feature]
            n = doc["pool"]["by_feature"][feature] * runs
            check.compare(cell, accuracy_cell(cell["correct"], n))
            total_right += cell["correct"]
        check.compare(cells["all"], accuracy_cell(total_right, n_calls))
    check.notes.append(
        "the right-answer counts per feature, the share of cant_tell answers and the count of "
        "malformed replies are as recorded: the run kept counts, not answers, so no reply is left "
        "to grade them from; the accuracies, intervals and cost are regraded"
    )
    return check


def check_cost_log(root: Path, log: Sequence[dict[str, Any]], claimed: set[int]) -> Check:
    """Every line of the cost log belongs to a paid run above, or is the one smoke call, or is a
    fake call that cost nothing."""
    from evals.paid_runs import PRICES_BEFORE_OPUS_5_5, SMOKE_PURPOSE, pricing_from

    check = Check("results/cost_log.jsonl", "the raw replies' token counts")
    smoke_pricing = pricing_from(PRICES_BEFORE_OPUS_5_5)
    real_total = 0.0
    for number, line in enumerate(log, start=1):
        if line.get("real") is True:
            real_total += float(line["cost_usd"])
        if number in claimed:
            continue
        if line.get("real") is not True:
            check.expect(f"line {number} (a fake call) cost_usd", line["cost_usd"], 0.0)
            check.expect(f"line {number} (a fake call) tokens", line["input_tokens"], 0)
        elif line.get("purpose") == SMOKE_PURPOSE:
            cost = smoke_pricing.cost_usd(
                line["model"], line["input_tokens"], line["output_tokens"], batch=False
            )
            check.expect(f"line {number} (the smoke call) cost_usd", line["cost_usd"], cost)
        else:
            check.problems.append(
                f"line {number}: a paid {line.get('purpose')} call that no fixture in "
                "evals/fixtures/raw accounts for"
            )
    check.notes.append(f"{real_total:.2f} USD paid in all, every line accounted for")
    return check


def check_inventory(root: Path) -> Check:
    """Every results file stamped real that a model run wrote is a paid run with a fixture."""
    from evals.paid_runs import PAID_RUNS

    check = Check("results/", "evals/paid_runs.py")
    listed = {run.results_name for run in PAID_RUNS}
    for path in sorted((root / "results").glob("*.json")):
        if not re.match(r"(model_sweep|benchmark|footage)_\d{8}T\d{6}Z\.json$", path.name):
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        if doc.get("real") is True and path.name not in listed:
            check.problems.append(
                f"{path.name} is a paid run with no raw replies: add it to evals/paid_runs.py "
                "and run evals/extract_raw.py"
            )
    for run in PAID_RUNS:
        if not (root / "evals" / "fixtures" / "raw" / run.fixture_name).is_file():
            check.problems.append(f"evals/fixtures/raw/{run.fixture_name} is missing")
    check.summary = (
        f"{len(PAID_RUNS)} paid runs, each with its raw replies in evals/fixtures/raw/, and no "
        "other paid run"
    )
    return check


def paid_checks(root: Path) -> list[Check]:
    from evals.extract_raw import load_cost_log
    from evals.paid_runs import PAID_RUNS

    inventory = check_inventory(root)
    if inventory.problems:
        return [inventory]
    log = load_cost_log(root / "results" / "cost_log.jsonl")
    checks: list[Check] = [inventory, check_key_frozen(root)]
    sweeps: dict[str, tuple[Any, list[Any]]] = {}
    claimed: set[int] = set()
    for run in PAID_RUNS:
        fixture = root / "evals" / "fixtures" / "raw" / run.fixture_name
        claimed.update(int(c["call"]) for c in fixture_calls(fixture))
        if run.kind == "model_sweep":
            check, records = check_sweep(run, root, log)
            sweeps[run.stamp] = (run, records)
            checks.append(check)
        elif run.kind == "footage":
            # The gate read the pass table the latest paid sweep before this run had written.
            made_at = load(f"results/{run.results_name}", root)["generated_at_utc"]
            before = [
                records
                for sweep_run, records in sweeps.values()
                if load(f"results/{sweep_run.results_name}", root)["generated_at_utc"] < made_at
            ]
            table = pass_table_of(before[-1], root) if before else {}
            checks.append(check_footage(run, root, log, table))
        elif run.kind == "benchmark":
            checks.append(check_benchmark(run, root, log))
    checks.extend(check_pass_table(sweeps, root))
    checks.append(check_footage_latest(root))
    checks.append(check_cost_log(root, log, claimed))
    return checks


# ---------------------------------------------------------------------------------------------
# Synthetic runs, made again from their seeds


def seeds(root: Path) -> dict[str, Any]:
    return load("evals/fixtures/seeds.json", root)


def fake_client(seed: int, items: Sequence[Any], root: Path) -> Any:
    from evals.model_sweep import FakeClient, FakeProfile

    profiles = {
        model: FakeProfile(
            accuracy={k: float(v) for k, v in p["accuracy"].items()},
            malformed_rate=float(p["malformed_rate"]),
        )
        for model, p in seeds(root)["fake_profiles"].items()
    }
    return FakeClient(seed=seed, profiles=profiles, items=items)


def blank_images(items: Sequence[Any]) -> dict[str, bytes]:
    """The fake client never looks at a photo, so none is read."""
    return {i.id: b"" for i in items}


def synthetic_sweep(rel: str, root: Path) -> tuple[Check, list[Any]]:
    from evals.model_sweep import Settings, load_questions, load_test_items, run_sweep

    doc = load(rel, root)
    check = Check(rel, f"seed {doc['seed']} and the fake profiles in evals/fixtures/seeds.json")
    items = load_test_items(root)
    models = list(dict.fromkeys(a["model"] for a in doc["answers"]))
    client = fake_client(int(doc["seed"]), items, root)
    records = run_sweep(
        client,
        models,
        items,
        load_questions(root),
        runs=int(doc["runs"]),
        settings=Settings(),
        images=blank_images(items),
    )
    check.compare(doc["answers"], [asdict(r) for r in records])
    check.compare(doc["counts"], sweep_counts(records))
    return check, records


def synthetic_benchmark(rel: str, root: Path, pool: Sequence[Any] | None) -> Check:
    from evals.benchmark import labelled_pool, per_feature_accuracy
    from evals.model_sweep import Settings, load_manifest, load_questions, run_sweep

    doc = load(rel, root)
    check = Check(rel, f"seed {doc['seed']} and the fake profiles in evals/fixtures/seeds.json")
    items = list(pool) if pool is not None else labelled_pool(load_manifest(root), root)
    if [i.id for i in items] != doc["pool"]["photo_ids"]:
        check.problems.append("the pool is not the photos this run used")
        return check
    models = list(doc["models"])
    records = run_sweep(
        fake_client(int(doc["seed"]), items, root),
        models,
        items,
        load_questions(root),
        runs=int(doc["runs"]),
        settings=Settings(),
        images=blank_images(items),
    )
    check.compare(doc["models"], per_feature_accuracy(records, models))
    check.expect("/cost_usd", doc["cost_usd"], 0.0)
    return check


def placeholder_pool(root: Path) -> list[Any]:
    from evals.model_sweep import Item

    return [
        Item(id=pid, feature=f, gold=g, photo_id=pid, photo_path=root, is_placeholder=True)
        for pid, f, g in seeds(root)["placeholder_pool"]["rows"]
    ]


def synthetic_footage(rel: str, root: Path, table: Mapping[str, Any]) -> Check:
    from evals.footage import adversarial, frame_items
    from evals.model_sweep import Query, load_manifest, load_questions, record_from
    from evals.paid_runs import PRICES_BEFORE_OPUS_5_5, pricing_from

    doc = load(rel, root)
    check = Check(rel, f"seed {doc['seed']} and the fake profiles in evals/fixtures/seeds.json")
    items = frame_items(load_manifest(root), root)
    questions = load_questions(root)
    client = fake_client(int(doc["seed"]), items, root)
    gold = {i.id: i.gold for i in items}
    records: list[Any] = []
    adv_out: dict[str, dict[str, dict[str, str]]] = {}
    for model in doc["models"]:
        queries = [
            Query(
                custom_id=f"{model}|{item.id}|r{run}",
                item_id=item.id,
                feature=item.feature,
                question=questions[item.feature],
                image_bytes=b"",
                model_id=model,
                run=run,
            )
            for run in range(int(doc["runs"]))
            for item in items
        ]
        raws = client.answer_many(queries)
        records.extend(
            record_from(q, r, gold[q.item_id]) for q, r in zip(queries, raws, strict=True)
        )
        answered, _adv = adversarial(client, [model], questions, int(doc["runs"]))
        for name, by_feature in answered.items():
            for feature, by_model in by_feature.items():
                adv_out.setdefault(name, {}).setdefault(feature, {}).update(by_model)
    regraded = footage_numbers(doc, records, table, root)
    regraded["adversarial"] = adv_out
    for key, value in regraded.items():
        check.compare({key: doc[key]}, {key: value})
    # A fake run spends nothing; its estimates used the prices of Sep 22.
    prices = pricing_from(PRICES_BEFORE_OPUS_5_5)
    estimates = expected_costs(doc["models"], prices, int(doc["runs"]), True, root)
    # evals/footage.py began to write the adversarial estimate at commit c49ba50, after this fake
    # run was made, so the file has none to compare.
    check.compare(
        doc["cost"],
        {"usd": 0.0, "per_100_frames_usd": 0.0, **estimates},
        skip=(r"/expected_adversarial_usd_by_model/.*",),
    )
    return check


def synthetic_analyses(root: Path, sweep_001651: Sequence[Any]) -> list[Check]:
    """The usability analysis, the three examples and the power simulation, from the plan seed."""
    from evals.common import PLAN_SEED
    from evals.make_synthetic_sessions import write_scenario
    from evals.model_sweep import item_accuracy, load_test_items
    from evals.pick_examples import best_model, pick
    from evals.power import main as power_main
    from evals.usability_analysis import DEFAULT_SCENARIO, N_BOOT, N_PERM, run

    checks: list[Check] = []
    with tempfile.TemporaryDirectory(prefix="second-look-reproduce-") as tmp:
        work = Path(tmp)
        data = write_scenario(DEFAULT_SCENARIO, work / "data", seed=PLAN_SEED)
        result = run(
            input_dir=data,
            out_dir=work / "out",
            synthetic=True,
            stamp_name="synthetic",
            scenario=DEFAULT_SCENARIO,
            n_boot=N_BOOT,
            n_perm=N_PERM,
            launch_utc=None,
        )
        usability = load("results/usability_synthetic.json", root)
        check = Check("results/usability_synthetic.json", f"plan seed {PLAN_SEED}")
        # The photo behind each item was renamed when the real photos came in; the item is the
        # same, and so is every number. run() adds the paths it wrote to after writing, and the
        # hash of the plan went into the file at commit 8b4b939, after this one was made.
        check.compare(
            usability,
            result,
            skip=(
                *STAMP_ONLY,
                r"/input",
                r"/per_item/t\d+/photo_id",
                r"/outputs/.*",
                r"/paths/.*",
                r"/plan_sha256",
            ),
        )
        checks.append(check)

        examples = load("results/examples.json", root)
        check = Check(
            "results/examples.json",
            "the regraded usability analysis and results/model_sweep_20260921T001651Z.json",
        )
        items = load_test_items(root)
        models = list(dict.fromkeys(r.model for r in sweep_001651))
        acc = item_accuracy(sweep_001651, models, items, real=False)["models"]
        name, mean_acc = best_model(acc)
        check.compare(
            {k: examples[k] for k in ("best_model", "examples")},
            {
                "best_model": {"model_id": name, "mean_accuracy": round(mean_acc, 4)},
                "examples": pick(result["per_item"], acc[name]),
            },
            skip=(r"/examples/\d+/photo_id",),
        )
        checks.append(check)

        power_out = work / "power.json"
        if quietly(power_main, ["--out", str(power_out)]) != 0:
            raise RuntimeError("evals/power.py failed")
        check = Check("results/power.json", f"plan seed {PLAN_SEED}")
        check.compare(
            load("results/power.json", root),
            json.loads(power_out.read_text(encoding="utf-8")),
            skip=STAMP_ONLY,
        )
        checks.append(check)
    return checks


def quietly(main: Callable[[list[str]], int], argv: list[str]) -> int:
    """Run a script's main without its own lines, which would bury the report."""
    with contextlib.redirect_stdout(io.StringIO()):
        return main(argv)


def check_coarseness(root: Path) -> Check:
    from evals import consensus_coarseness

    check = Check("results/consensus_coarseness.json", "its seed, by make consensus-check")
    if quietly(consensus_coarseness.main, ["--check"]) != 0:
        check.problems.append("evals/consensus_coarseness.py --check found a difference")
    doc = load("results/consensus_coarseness.json", root)
    check.values = sum(1 for _p, v in leaves(doc) if is_graded(v))
    return check


def not_regraded() -> list[Check]:
    out = []
    for path, why in (
        (
            "results/ablation_20260921T001415Z.json",
            "its rule stub is keyed to the bytes of gray placeholder images the repository no "
            "longer has",
        ),
        (
            "results/consensus_synthetic.json",
            "made by an earlier rule of evals/consensus.py that was dropped as biased "
            "(docs/DECISIONS.md, 2026-09-23); today's script makes a different file",
        ),
        (
            "results/agreement_20260921T001415Z.json",
            "no model and no seed: it counts the two label columns of the photo manifest as it "
            "stood on Sep 20, with 18 gray placeholders the repository no longer has",
        ),
    ):
        check = Check(path, "none", regraded=False)
        check.summary = f"not regraded: {why}"
        out.append(check)
    return out


def synthetic_checks(root: Path) -> list[Check]:
    checks: list[Check] = []
    sweeps: dict[str, list[Any]] = {}
    for stamp in ("20260921T001414Z", "20260921T001651Z", "20260922T054916Z"):
        check, records = synthetic_sweep(f"results/model_sweep_{stamp}.json", root)
        sweeps[stamp] = records
        checks.append(check)
    checks.append(
        synthetic_benchmark("results/benchmark_20260921T001415Z.json", root, placeholder_pool(root))
    )
    checks.append(synthetic_benchmark("results/benchmark_20260922T054932Z.json", root, None))
    # The fake footage run read the fake pass table of the sweep before it, which licenses no
    # flag at all (rule 4), so every candidate is dropped.
    fake_table = pass_table_of(sweeps["20260922T054916Z"], root) | {"real": False}
    checks.append(synthetic_footage("results/footage_20260922T184011Z.json", root, fake_table))
    checks.extend(synthetic_analyses(root, sweeps["20260921T001651Z"]))
    checks.append(check_coarseness(root))
    checks.extend(not_regraded())
    return checks


# ---------------------------------------------------------------------------------------------
# The run


def report(checks: Sequence[Check], out: Callable[[str], None] = print) -> int:
    failed = [c for c in checks if c.problems]
    for c in checks:
        mark = "FAIL" if c.problems else ("ok  " if c.regraded else "skip")
        line = c.summary or f"{c.values} values regraded from {c.source}"
        out(f"{mark} {c.path}: {line}")
        for problem in c.problems[:8]:
            out(f"       {problem}")
        if len(c.problems) > 8:
            out(f"       and {len(c.problems) - 8} more")
        for note in c.notes:
            out(f"       note: {note}")
    total = sum(c.values for c in checks)
    if failed:
        out(f"reproduce: {len(failed)} of {len(checks)} files differ from the raw replies or seeds")
        return 1
    # A skipped file is not a regraded one, and a note names numbers kept as recorded, so the last
    # line counts them apart instead of folding them into "regraded" (judge walk 01, R02).
    regraded = sum(1 for c in checks if c.regraded)
    skipped = len(checks) - regraded
    notes = sum(len(c.notes) for c in checks)
    rest = ""
    if skipped or notes:
        rest = f"; {skipped} files not regraded and {notes} notes, each named above"
    out(
        f"reproduce: {total} values in {regraded} files regraded from raw replies and seeds, "
        f"with no network and no key; every one matches{rest}"
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    parser.add_argument("--paid-only", action="store_true", help="skip the synthetic runs")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    for name in KEY_NAMES:
        os.environ.pop(name, None)

    from scripts.seed_demo import NoNetwork

    guard = NoNetwork()
    guard.install()
    try:
        checks = paid_checks(root)
        if not args.paid_only:
            checks += synthetic_checks(root)
    finally:
        guard.remove()
    code = report(checks)
    if guard.tried:
        print(f"reproduce: something tried the network: {', '.join(guard.tried[:3])}")
        return 1
    return code


if __name__ == "__main__":
    sys.exit(main())
