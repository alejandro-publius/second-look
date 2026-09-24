"""One footage frame where the gate kept a flag, and one where it dropped one (CRITIC_02 D04).

A judge can see the AI act here without a key: what a model answered about a real creek frame,
what core/gate.py made of that answer, and the question core/followups.py would then let the
checker ask. It reads only committed files, and calls no model and no network:

- the answers of the paid footage run that results/footage_latest.json is, from its fixture in
  evals/fixtures/raw/ (the one whose first line names that run);
- results/model_pass_table.json, the pass table that run's gate read. It was written before the
  run, and the script stops if it is not;
- photos/manifest.csv, for each frame's file and credit;
- content/, loaded by core.content_loader the way the API loads it, for the question wording,
  the follow-up rules, the form and the words on screen.

Every yes answer becomes a candidate flag and goes through the gate the way evals/footage.py does
it: evals.footage.candidate_flag, then core.gate.parse_flags with the model and the pass table.

The pick rule (PICK_RULE below): only candidates on a feature the creek check asks about, one
with an item in content/form.yaml, in order by frame id, then model id, feature and run. The kept
case is the first of them the gate kept, the dropped case the first it dropped (CRITIC_06 H02: a
kept flag on the dug-out channel, which the check never asks about, is not an example of what a
person would see). The files also say how many kept flags there are on each feature, and
whether a kept flag on it makes a question eligible at all.

The kept flag then goes to core.followups.select_followups the way apps/api/check.py calls it,
with this one flag, no answers, no test score, rain unknown and the checker switched on. The live
site runs with the checker off, and both files say so.

Writes examples/footage-flag/example.json and examples/footage-flag/README.md. The page is made
from the same data as the JSON, so the two cannot drift apart.

Run: uv run python evals/footage_example.py            writes both files
     uv run python evals/footage_example.py --check    fails unless both committed files are
                                                       what it writes; make check runs this
                                                       through evals/tests/test_footage_example.py
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.checker import NOTE_MAX_CHARS, feature_passed
from core.content_loader import Content, load_content
from core.followups import SiteContext, select_followups
from core.gate import Flag, parse_flags
from core.records import FEATURES
from evals.footage import candidate_flag

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = "evals/footage_example.py"
OUT_DIR = Path("examples") / "footage-flag"
OUT_JSON = OUT_DIR / "example.json"
OUT_README = OUT_DIR / "README.md"
RAW_DIR = Path("evals") / "fixtures" / "raw"
LATEST = Path("results") / "footage_latest.json"
PASS_TABLE = Path("results") / "model_pass_table.json"
MANIFEST = Path("photos") / "manifest.csv"
# From the README folder back to the repository root, for the page's links.
UP = "../../"

PICK_RULE = (
    "Every yes answer in the run is a candidate flag. Only the candidates on a feature the creek "
    "check asks about, one with an item in content/form.yaml, are picked from. They are put in "
    "order by frame id, then model id, feature and run. The kept case is the first of them the "
    "gate kept, and the dropped case is the first of them the gate dropped."
)
FOLLOWUP_CALL = (
    "core.followups.select_followups, called the way apps/api/check.py calls it, with the flags "
    "shown here, no answers, no test score, rain unknown, the rules in content/followups.yaml, "
    "the form in content/form.yaml and the checker switched on"
)
LIVE_SITE = (
    "On the live site the checker is off today (CHECKER_ENABLED), so no volunteer has seen a "
    "checker question. This is the paid footage run's record, not something a volunteer saw."
)
MANIFEST_FIELDS = ("id", "file", "source_url", "author", "license", "coarse_location", "gold_label")


@dataclass(frozen=True)
class Candidate:
    """One yes answer of the run, and what the gate made of it."""

    line_number: int  # counted from 1, the fixture's first line included
    line: str  # the line exactly as committed
    answer: dict[str, Any]
    candidate: dict[str, Any]
    flags: list[Flag]
    reasons: list[str]

    @property
    def order(self) -> tuple[str, str, str, int]:
        a = self.answer
        return (str(a["frame"]), str(a["model"]), str(a["feature"]), int(a["run"]))


def load_json(root: Path, rel: Path) -> Any:
    return json.loads((root / rel).read_text(encoding="utf-8"))


def fixture_lines(path: Path) -> list[str]:
    """The lines of a fixture as committed, split on newlines only."""
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    return lines[:-1] if lines and lines[-1] == "" else lines


def run_fixture(root: Path, latest: Mapping[str, Any]) -> tuple[Path, dict[str, Any]]:
    """The raw fixture of the run results/footage_latest.json is: its first line names that run."""
    found: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted((root / RAW_DIR).glob("footage_*.jsonl")):
        head = json.loads(fixture_lines(path)[0])
        if head.get("generated_at_utc") == latest.get("generated_at_utc"):
            found.append((path, head))
    if len(found) != 1:
        raise SystemExit(
            f"footage-example: {len(found)} fixtures in {RAW_DIR} match {LATEST}, not 1; "
            "run evals/extract_raw.py after a paid footage run"
        )
    return found[0]


def answers_of(lines: Sequence[str]) -> list[tuple[int, str, dict[str, Any]]]:
    """Every answer line with its number; the first line and the call lines are left out."""
    out: list[tuple[int, str, dict[str, Any]]] = []
    for number, line in enumerate(lines, start=1):
        if number == 1 or not line.strip():
            continue
        doc = json.loads(line)
        if "frame" in doc:
            out.append((number, line, doc))
    return out


def candidates(
    answers: Sequence[tuple[int, str, dict[str, Any]]], pass_table: Mapping[str, Any]
) -> list[Candidate]:
    """Each yes answer through the gate, as evals/footage.py gate_outcome sends it."""
    out: list[Candidate] = []
    for number, line, a in answers:
        if a["malformed"] or a["answer"] != "yes":
            continue
        candidate = candidate_flag(str(a["feature"]), str(a["note"]))
        flags, reasons = parse_flags(candidate, model_id=str(a["model"]), pass_table=pass_table)
        out.append(Candidate(number, line, a, candidate, flags, reasons))
    return out


def asked_features(content: Content) -> list[str]:
    """The features the creek check asks about: each one a form item names, in FEATURES order."""
    named = {item.get("feature") for item in content.form.get("items", [])}
    return [f for f in FEATURES if f in named]


def kept_by_feature(found: Sequence[Candidate]) -> dict[str, int]:
    """How many flags the gate kept on each feature, every feature named, in FEATURES order."""
    counts = Counter(str(c.answer["feature"]) for c in found if c.flags)
    return {f: counts.get(f, 0) for f in FEATURES}


def pick(found: Sequence[Candidate], asked: Sequence[str]) -> tuple[Candidate, Candidate]:
    """PICK_RULE: among candidates on an asked feature, the first kept and the first dropped."""
    ordered = sorted((c for c in found if c.answer["feature"] in asked), key=lambda c: c.order)
    kept = next((c for c in ordered if c.flags), None)
    dropped = next((c for c in ordered if not c.flags), None)
    if kept is None or dropped is None:
        raise SystemExit(
            "footage-example: the run has no kept flag or no dropped flag on a feature the creek "
            "check asks about"
        )
    return kept, dropped


def manifest_row(root: Path, frame: str) -> dict[str, str]:
    with (root / MANIFEST).open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["id"] == frame:
                return {k: row.get(k, "") for k in MANIFEST_FIELDS}
    raise SystemExit(f"footage-example: frame {frame} has no row in {MANIFEST}")


def pass_cell(pass_table: Mapping[str, Any], model: str, feature: str) -> dict[str, Any]:
    """What the pass table says about this model and feature, counted from its own runs."""
    runs = pass_table["models"][model][feature]["runs"]
    return {
        "passed": feature_passed(pass_table, model, feature),
        "runs": len(runs),
        "runs_with_every_photo_right": sum(1 for r in runs if all(r)),
        "photos_per_run": len(runs[0]) if runs else 0,
        "pass_rule": pass_table["pass_rule"],
    }


def others(
    answers: Sequence[tuple[int, str, dict[str, Any]]],
    frame: str,
    feature: str,
    models: Sequence[str],
    pass_table: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Every model's answers on the same frame and feature, run by run, in the order they ran."""
    rows: list[dict[str, Any]] = []
    for model in models:
        mine = sorted(
            (
                a
                for _n, _l, a in answers
                if (a["frame"], a["feature"], a["model"]) == (frame, feature, model)
            ),
            key=lambda a: int(a["run"]),
        )
        rows.append(
            {
                "model": model,
                "passed_this_feature": feature_passed(pass_table, model, feature),
                "answers_by_run": [str(a["answer"]) for a in mine],
            }
        )
    return rows


def fill(template: str, params: Mapping[str, Any]) -> str:
    """A locale string with its {name} parts filled, the way apps/web/lib/t.ts fills them."""
    return re.sub(r"\{(\w+)\}", lambda m: str(params[m[1]]) if m[1] in params else m[0], template)


def feature_row(content: Content, feature: str) -> Mapping[str, Any]:
    for row in content.features:
        if row.get("id") == feature:
            return row
    raise SystemExit(f"footage-example: {feature} is not in content/features.yaml")


def followups(content: Content, flags: Sequence[Flag], *, checker_on: bool) -> list[dict[str, Any]]:
    chosen = select_followups(
        {},
        SiteContext(rain="unknown"),
        None,
        flags,
        content.followups,
        form_items=content.form.get("items", []),
        checker_enabled=checker_on,
    )
    return [f.model_dump(mode="json") for f in chosen]


def kept_flag_asks(content: Content, found: Sequence[Candidate]) -> dict[str, bool]:
    """For each feature with a kept flag: does the first of them, in PICK_RULE order, make a
    question eligible? core/followups.py asks only about a feature the creek check asks about."""
    asks: dict[str, bool] = {}
    for c in sorted(found, key=lambda c: c.order):
        feature = str(c.answer["feature"])
        if c.flags and feature not in asks:
            asks[feature] = bool(followups(content, c.flags, checker_on=True))
    return {f: asks[f] for f in FEATURES if f in asks}


def on_screen(content: Content, followup: Mapping[str, Any]) -> dict[str, Any]:
    """The words the walk page shows for a checker question (apps/web/components/WalkFlow.tsx):
    the question with the feature's plain words, the flag's note after "the checker noticed",
    then the two buttons. Only the note is model text."""
    params = followup["params"]
    plain = feature_row(content, str(params["feature"]))["plain"]
    locale = content.locale
    return {
        "question": fill(locale[str(followup["question_key"])], {"note": plain}),
        "label": locale["label.checker_noticed"],
        "note": params["note"],
        "buttons": [locale["check.looked_again"], locale["check.skip"]],
    }


def case(
    c: Candidate,
    *,
    root: Path,
    content: Content,
    fixture_rel: str,
    answers: Sequence[tuple[int, str, dict[str, Any]]],
    models: Sequence[str],
    pass_table: Mapping[str, Any],
) -> dict[str, Any]:
    a = c.answer
    model, feature, frame = str(a["model"]), str(a["feature"]), str(a["frame"])
    eligible = followups(content, c.flags, checker_on=True)
    doc: dict[str, Any] = {
        "frame": frame,
        "manifest_row": manifest_row(root, frame),
        "model": model,
        "feature": feature,
        "run": int(a["run"]),
        "question_asked": feature_row(content, feature)["question"],
        "raw_line": {"file": fixture_rel, "line_number": c.line_number, "text": c.line},
        "candidate_flag": c.candidate,
        "gate": {
            "kept": bool(c.flags),
            "flags": [f.model_dump(mode="json") for f in c.flags],
            "drop_reasons": list(c.reasons),
        },
        "pass_table_cell": pass_cell(pass_table, model, feature),
        "followup": {
            "called_with": FOLLOWUP_CALL,
            "eligible": eligible,
            "with_the_checker_off": followups(content, c.flags, checker_on=False),
        },
        "same_frame_and_feature": others(answers, frame, feature, models, pass_table),
    }
    if eligible:
        doc["followup"]["on_screen"] = on_screen(content, eligible[0])
    return doc


@dataclass(frozen=True)
class Run:
    """The footage run of results/footage_latest.json, its raw answers and the gate over them."""

    latest: dict[str, Any]
    fixture: Path
    head: dict[str, Any]
    pass_table: dict[str, Any]
    answers: list[tuple[int, str, dict[str, Any]]]
    found: list[Candidate]
    counts: dict[str, int]


def load_run(root: Path = ROOT) -> Run:
    """Every yes answer of the latest real footage run through the gate, from committed files.

    Stops unless the run is real, its pass table came first, and the gate gives the numbers
    results/footage_latest.json holds. evals/model_card.py reads the kept flags by feature here.
    """
    latest = load_json(root, LATEST)
    if latest.get("real") is not True:
        raise SystemExit(f"footage-example: {LATEST} is not a real run, so it shows no flag")
    fixture, head = run_fixture(root, latest)
    pass_table = load_json(root, PASS_TABLE)
    if not str(pass_table.get("generated_at_utc", "")) < str(latest["generated_at_utc"]):
        raise SystemExit(
            f"footage-example: {PASS_TABLE} was written after the footage run, so it is not the "
            "table that run's gate read"
        )
    answers = answers_of(fixture_lines(fixture))
    found = candidates(answers, pass_table)
    counts = {
        "candidates": len(found),
        "kept": sum(1 for c in found if c.flags),
        "dropped": sum(1 for c in found if not c.flags),
    }
    committed = {k: latest["gate"][k] for k in counts}
    if counts != committed:
        raise SystemExit(
            f"footage-example: the gate gives {counts} on {RAW_DIR} with {PASS_TABLE}, but "
            f"{LATEST} says {committed}; make reproduce says which is wrong"
        )
    return Run(latest, fixture, head, pass_table, answers, found, counts)


def build(root: Path = ROOT) -> dict[str, Any]:
    run = load_run(root)
    latest, fixture, head, pass_table = run.latest, run.fixture, run.head, run.pass_table
    answers, found, counts = run.answers, run.found, run.counts
    content = load_content(root)
    asked = asked_features(content)
    kept, dropped = pick(found, asked)
    fixture_rel = fixture.relative_to(root).as_posix()
    common: dict[str, Any] = {
        "root": root,
        "content": content,
        "fixture_rel": fixture_rel,
        "answers": answers,
        "models": list(latest["models"]),
        "pass_table": pass_table,
    }
    return {
        "what": (
            "One frame of the paid footage run where core/gate.py kept a model's flag, and one "
            "where it dropped one, with the question the kept flag makes eligible"
        ),
        "written_by": SCRIPT,
        "live_site": LIVE_SITE,
        "run": {
            "results": head["run"],
            "generated_at_utc": latest["generated_at_utc"],
            "raw_answers": fixture_rel,
            "raw_answers_kept": head["kept"],
            "pass_table": PASS_TABLE.as_posix(),
            "pass_table_generated_at_utc": pass_table["generated_at_utc"],
        },
        "pick_rule": PICK_RULE,
        "gate_over_the_run": counts,
        "kept_by_feature": kept_by_feature(found),
        "features_the_check_asks_about": asked,
        "a_kept_flag_asks": kept_flag_asks(content, found),
        "kept": case(kept, **common),
        "dropped": case(dropped, **common),
    }


# The page ---------------------------------------------------------------------------------------


def link(rel: str) -> str:
    return f"[`{rel}`]({UP}{rel})"


def credit(row: Mapping[str, str]) -> str:
    return (
        f"Frame `{row['id']}` from {row['source_url']}, by {row['author']}, licence "
        f"{row['license']}. File {link('photos/' + row['file'])}, with its row in "
        f"{link(MANIFEST.as_posix())}."
    )


def frame_alt(frame: str) -> str:
    """The frame's alt text from the locale, which says what is in it and not what any model made
    of it (apps/web/scripts/build-content.mjs gives /how-we-know the same words)."""
    locale = json.loads((ROOT / "content" / "locales" / "en.json").read_text(encoding="utf-8"))
    return str(locale.get(f"photo.alt.{frame}", ""))


def others_table(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    out = [
        "| Model | Passed this feature on the 16-photo test | Its answers, run by run |",
        "|---|---|---|",
    ]
    for r in rows:
        passed = "yes" if r["passed_this_feature"] else "no"
        out.append(f"| `{r['model']}` | {passed} | {', '.join(r['answers_by_run'])} |")
    return out


def cell_words(cell: Mapping[str, Any]) -> str:
    return (
        f"it got all {cell['photos_per_run']} photos of that feature right in "
        f"{cell['runs_with_every_photo_right']} of {cell['runs']} runs. The rule is: "
        f"{cell['pass_rule']}."
    )


def section(title: str, c: Mapping[str, Any], raw_kept: str) -> list[str]:
    row = c["manifest_row"]
    raw = c["raw_line"]
    gate = c["gate"]
    cell = c["pass_table_cell"]
    fu = c["followup"]
    alt = f"Frame {row['id']}, a still from a creek video filmed in {row['coarse_location']}"
    lines = [
        f"## {title}: frame `{c['frame']}`",
        "",
        f"![{alt}]({UP}photos/{row['file']})",
        "",
        credit(row),
        "",
        f"1. **What the model was asked.** `{c['model']}` was asked the frozen question for "
        f'`{c["feature"]}` from {link("content/features.yaml")}: "{c["question_asked"]}" '
        f"This is its answer from run {c['run']} (the runs are numbered from 0).",
        f"2. **What the model answered.** Line {raw['line_number']} of {link(raw['file'])}, "
        "exactly as committed:",
        "",
        "   ```json",
        f"   {raw['text']}",
        "   ```",
        "",
        f'   The fixture\'s first line says what it holds: "{raw_kept}". So this is the answer '
        "after `force_answer` in "
        f"{link('core/checker.py')} made it yes, no or can't tell with a short note, not the "
        "reply exactly as the model sent it.",
        "3. **What the gate did.** The answer yes became the candidate flag "
        f"`{json.dumps(c['candidate_flag'], ensure_ascii=False)}` (`candidate_flag` in "
        f"{link('evals/footage.py')}), and `parse_flags` in {link('core/gate.py')} read it "
        f"with the model's name and {link(PASS_TABLE.as_posix())}.",
    ]
    if gate["kept"]:
        flag = gate["flags"][0]
        lines += [
            "",
            f"   It kept it, as this Flag: `{json.dumps(flag, ensure_ascii=False)}`. The pass "
            f"table says `{c['model']}` passed `{c['feature']}`: {cell_words(cell)}",
        ]
        if len(flag["note"]) == NOTE_MAX_CHARS:
            lines[-1] += (
                f" The note is {NOTE_MAX_CHARS} characters long, the most `force_answer` keeps, "
                "so it is cut off there."
            )
    else:
        reasons = "; ".join(f'"{r}"' for r in gate["drop_reasons"])
        lines += [
            "",
            f"   It dropped it. The gate's reason, in its own words: {reasons}. The pass table "
            f"says `{c['model']}` did not pass `{c['feature']}`: {cell_words(cell)}",
        ]
    lines.append("4. **What a person would then be asked.** " + asked_words(fu))
    if "on_screen" in fu:
        screen = fu["on_screen"]
        buttons = " ".join(f"[{b}]" for b in screen["buttons"])
        lines += [
            "",
            f"   > **{screen['question']}**",
            "   >",
            f"   > {screen['label']}: {screen['note']}",
            "   >",
            f"   > {buttons}",
            "",
            "   Those are the words the walk page shows for a checker question "
            f"({link('apps/web/components/WalkFlow.tsx')}): the question with the feature's "
            'plain words, then the model\'s note, and only there, after "the checker noticed". '
            "With the checker off, as on the live site today, the same call "
            f"{'asks nothing' if not fu['with_the_checker_off'] else 'still asks'}.",
            "",
            f"   The person taps {' or '.join(chr(34) + b + chr(34) for b in screen['buttons'])}, "
            "and no stored answer changes: the question asks them to look again, and the "
            "answers they gave before it stay as they were.",
        ]
    lines += [
        "5. **What every model answered on this frame and feature.** From the same file.",
        "",
        *[f"   {x}" for x in others_table(c["same_frame_and_feature"])],
        "",
    ]
    lines.append("   Only a yes becomes a candidate flag. A no or a can't tell proposes nothing.")
    lines.append("")
    gold = row["gold_label"].strip()
    if gold:
        lines.append(f"   The frame's label for this feature, from the manifest: {gold}.")
    elif gate["kept"]:
        lines.append(
            "   The frame has no label in the manifest, so nobody has said whether the model was "
            "right. The flag decides nothing either way: it only lets the checker ask the person "
            "to look again, and what is kept is the person's answer."
        )
        # CRITIC_07 J03: say what the frame shows, from its alt text, and whether any other model
        # that passed this feature agreed with the flag.
        others = [
            r
            for r in c["same_frame_and_feature"]
            if r["passed_this_feature"] and r["model"] != c["model"]
        ]
        shows = frame_alt(str(row["id"]))
        if others and not any("yes" in r["answers_by_run"] for r in others):
            lines.append("")
            lines.append(
                (f"   What the frame shows, from its alt text: {shows} " if shows else "   ")
                + "No other model that passed this feature said yes on it. Passing the photos "
                "did not stop this flag, which is why a flag can only ask the person to look "
                "again and never answers for them."
            )
    else:
        lines.append(
            "   The frame has no label in the manifest, so nobody has said whether the model was "
            "right. The gate does not judge that: it dropped the flag because this model did not "
            "pass this feature on the test, whatever the frame shows."
        )
    lines.append("")
    return lines


def asked_words(fu: Mapping[str, Any]) -> str:
    call = (
        f"`select_followups` in {link('core/followups.py')}, called the way "
        f"{link('apps/api/check.py')} calls it, with no answers, no test score, rain unknown, "
        f"the rules in {link('content/followups.yaml')} and the checker switched on"
    )
    eligible = fu["eligible"]
    if not eligible:
        return (
            f"Nothing from the checker. The gate kept no flag, so {call}, and no flag, makes no "
            "question eligible."
        )
    ids = ", ".join(f"`{f['rule_id']}`" for f in eligible)
    return (
        f"{call[0].upper()}{call[1:]}, and this one flag, makes one question eligible: {ids}. It "
        "is a pure function: it reads no file, calls no model and uses no network."
    )


def by_feature_words(doc: Mapping[str, Any]) -> str:
    """The kept flags by feature, and which features the creek check asks about."""
    kept = doc["kept_by_feature"]
    asked = list(doc["features_the_check_asks_about"])
    unasked = [f for f in kept if f not in asked]
    split = ", ".join(f"`{f}` {n}" for f, n in kept.items())
    words = (
        f"- The {doc['gate_over_the_run']['kept']} kept flags by feature: {split}. The creek "
        f"check has an item in {link('content/form.yaml')} for {and_list(asked)}"
    )
    if unasked:
        words += f", and none for {and_list(unasked)}"
    words += "."
    asks = doc["a_kept_flag_asks"]
    silent = [f for f in unasked if f in asks]
    if silent and not any(asks[f] for f in silent):
        words += (
            f" So a kept flag on {and_list(silent)} makes no question eligible: `select_followups` "
            f"in {link('core/followups.py')} asks only about a feature the check has an item for."
        )
    return words


def and_list(features: Sequence[str]) -> str:
    names = [f"`{f}`" for f in features]
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}"


def readme(doc: Mapping[str, Any]) -> str:
    run = doc["run"]
    cands = doc["gate_over_the_run"]
    kept_words = run["raw_answers_kept"]
    lines = [
        "# The checker on real creek footage: one flag kept, one dropped",
        "",
        f"{doc['live_site']}",
        "",
        f"This page and [`{OUT_JSON.name}`]({OUT_JSON.name}) are written by {link(SCRIPT)} from "
        "committed files only. No model was called to make them. `make check` fails if either "
        "is not what the script writes.",
        "",
        "## Where it comes from",
        "",
        f"- The run: {link(run['results'])}, made at {run['generated_at_utc']}. Its answers are "
        f"in {link(run['raw_answers'])}.",
        f"- The pass table its gate read: {link(run['pass_table'])}, made at "
        f"{run['pass_table_generated_at_utc']}, before the run.",
        f"- In that run, {cands['candidates']} answers were yes, so {cands['candidates']} "
        f"candidate flags went through the gate: {cands['kept']} kept and {cands['dropped']} "
        f"dropped. These are the gate numbers in {link(LATEST.as_posix())}; the script stops if "
        "they differ.",
        by_feature_words(doc),
        f"- How the two frames were picked, by a fixed rule. {doc['pick_rule']}",
        "",
        *section("Kept", doc["kept"], kept_words),
        *section("Dropped", doc["dropped"], kept_words),
    ]
    return "\n".join(lines).rstrip("\n") + "\n"


# Writing and checking -----------------------------------------------------------------------------


def dumps(doc: Mapping[str, Any]) -> str:
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def outputs(root: Path = ROOT) -> dict[Path, str]:
    doc = build(root)
    return {OUT_JSON: dumps(doc), OUT_README: readme(doc)}


def main(argv: list[str] | None = None, *, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail if a committed file differs")
    args = parser.parse_args(argv)
    wanted = outputs(root)
    if args.check:
        stale = [
            rel.as_posix()
            for rel, text in wanted.items()
            if not (root / rel).is_file() or (root / rel).read_text(encoding="utf-8") != text
        ]
        if stale:
            print(f"footage-example: {', '.join(stale)} out of date; run uv run python {SCRIPT}")
            return 1
        print(f"footage-example: {OUT_DIR.as_posix()}/ matches the committed run")
        return 0
    for rel, text in wanted.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    doc = json.loads(wanted[OUT_JSON])
    print(
        f"footage-example: kept {doc['kept']['frame']} ({doc['kept']['model']}, "
        f"{doc['kept']['feature']}), dropped {doc['dropped']['frame']} "
        f"({doc['dropped']['model']}, {doc['dropped']['feature']}); wrote {OUT_DIR.as_posix()}/"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
