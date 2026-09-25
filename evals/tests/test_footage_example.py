"""The footage example is what the committed files give, and each step is the product's own code.

examples/footage-flag/ shows one frame where the gate kept a model's flag and one where it dropped
one. These tests work each step out again from the committed files, without the example's own
helpers where they can, so a broken pick rule or a gate call that is not the real one turns red.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from core.content_loader import load_content
from core.followups import SiteContext, select_followups
from core.gate import parse_flags
from core.records import FEATURES
from evals import footage, footage_example
from evals.reproduce import footage_records

ROOT = Path(__file__).resolve().parents[2]
LATEST = json.loads((ROOT / "results" / "footage_latest.json").read_text(encoding="utf-8"))
TABLE = json.loads((ROOT / "results" / "model_pass_table.json").read_text(encoding="utf-8"))
DOC: dict[str, Any] = json.loads((ROOT / footage_example.OUT_JSON).read_text(encoding="utf-8"))
PAGE = (ROOT / footage_example.OUT_README).read_text(encoding="utf-8")
FORM_ITEMS: list[dict[str, Any]] = yaml.safe_load(
    (ROOT / "content" / "form.yaml").read_text(encoding="utf-8")
)["items"]
# The features the creek check asks about, read from the form here and not by the example's code.
ASKED = {item["feature"] for item in FORM_ITEMS if item.get("feature")}


def fixture() -> Path:
    return ROOT / DOC["run"]["raw_answers"]


def lines() -> list[str]:
    return fixture().read_text(encoding="utf-8").split("\n")


def gate(answer: dict[str, Any]) -> tuple[list[Any], list[str]]:
    """The gate on one answer, the way evals/footage.py calls it."""
    candidate = footage.candidate_flag(answer["feature"], answer["note"])
    return parse_flags(candidate, model_id=answer["model"], pass_table=TABLE)


def test_the_committed_files_are_what_the_script_writes() -> None:
    assert DOC == footage_example.build(), "run: uv run python evals/footage_example.py"
    assert footage_example.main(["--check"]) == 0


def test_check_fails_when_the_page_drifts(monkeypatch: pytest.MonkeyPatch) -> None:
    real = footage_example.readme
    monkeypatch.setattr(footage_example, "readme", lambda doc: real(doc) + "one more line\n")
    assert footage_example.main(["--check"]) == 1


def test_the_run_is_the_latest_real_footage_run_and_its_table_came_first() -> None:
    head = json.loads(lines()[0])
    assert LATEST["real"] is True
    assert head["generated_at_utc"] == LATEST["generated_at_utc"] == DOC["run"]["generated_at_utc"]
    assert head["run"] == DOC["run"]["results"]
    assert TABLE["generated_at_utc"] < LATEST["generated_at_utc"]


def test_the_gate_over_the_whole_run_gives_the_committed_numbers() -> None:
    """The table the example reads is the one the run's gate read: every number agrees."""
    answers = [json.loads(x) for x in lines()[1:] if x.strip()]
    got = footage.gate_outcome(footage_records(answers), TABLE)
    assert got == LATEST["gate"]
    assert DOC["gate_over_the_run"] == {k: got[k] for k in ("candidates", "kept", "dropped")}


def test_the_two_frames_follow_the_pick_rule() -> None:
    """On a feature the check asks about, first kept and first dropped, by frame id, then model,
    feature and run (CRITIC_06 H02)."""
    assert "dug_out_channel" not in ASKED and "artificial_bank" in ASKED
    rows: list[tuple[tuple[str, str, str, int], int, bool]] = []
    for number, line in enumerate(lines(), start=1):
        if number == 1 or not line.strip():
            continue
        a = json.loads(line)
        if "frame" not in a or a["malformed"] or a["answer"] != "yes":
            continue
        if a["feature"] not in ASKED:
            continue
        flags, _reasons = gate(a)
        rows.append(((a["frame"], a["model"], a["feature"], int(a["run"])), number, bool(flags)))
    rows.sort()
    first_kept = next(r for r in rows if r[2])
    first_dropped = next(r for r in rows if not r[2])
    for name, want in (("kept", first_kept), ("dropped", first_dropped)):
        case = DOC[name]
        assert (case["frame"], case["model"], case["feature"], case["run"]) == want[0]
        assert case["raw_line"]["line_number"] == want[1]
    assert DOC["kept"]["frame"] != DOC["dropped"]["frame"]
    assert footage_example.PICK_RULE in PAGE
    assert DOC["kept"]["feature"] in ASKED and DOC["dropped"]["feature"] in ASKED
    assert DOC["features_the_check_asks_about"] == [f for f in FEATURES if f in ASKED]


def test_the_kept_flags_by_feature_are_counted_again_from_the_raw_answers() -> None:
    """CRITIC_06 H02: how many kept flags are on each feature, worked out here from the raw file
    through the gate, every feature named, and on the page in the same words."""
    kept: dict[str, int] = dict.fromkeys(FEATURES, 0)
    for number, line in enumerate(lines(), start=1):
        if number == 1 or not line.strip():
            continue
        a = json.loads(line)
        if "frame" not in a or a["malformed"] or a["answer"] != "yes":
            continue
        flags, _reasons = gate(a)
        for f in flags:
            kept[f.feature] += 1
    assert DOC["kept_by_feature"] == kept
    assert sum(kept.values()) == LATEST["gate"]["kept"] == DOC["gate_over_the_run"]["kept"]
    split = ", ".join(f"`{f}` {n}" for f, n in kept.items())
    assert f"- The {LATEST['gate']['kept']} kept flags by feature: {split}. " in PAGE
    assert "and none for `dug_out_channel`." in PAGE


def test_each_raw_line_is_the_committed_line_word_for_word() -> None:
    committed = lines()
    for name in ("kept", "dropped"):
        raw = DOC[name]["raw_line"]
        assert raw["file"] == DOC["run"]["raw_answers"]
        assert committed[raw["line_number"] - 1] == raw["text"]
        assert f"   {raw['text']}\n" in PAGE
        a = json.loads(raw["text"])
        assert (a["frame"], a["model"], a["feature"], a["run"], a["answer"]) == (
            DOC[name]["frame"],
            DOC[name]["model"],
            DOC[name]["feature"],
            DOC[name]["run"],
            "yes",
        )


def test_the_dropped_reason_is_the_gates_own_words() -> None:
    case = DOC["dropped"]
    answer = json.loads(case["raw_line"]["text"])
    flags, reasons = gate(answer)
    assert flags == [] and case["gate"]["flags"] == [] and case["gate"]["kept"] is False
    assert case["gate"]["drop_reasons"] == reasons
    assert reasons == [f"flag 1: feature {answer['feature']} not passed by model {answer['model']}"]
    # One of the reasons results/footage_latest.json counts, with the gate's "flag 1: " cut off.
    assert reasons[0].split(": ", 1)[1] in LATEST["gate"]["drop_reasons"]
    assert TABLE["models"][answer["model"]][answer["feature"]]["passed"] is False
    assert f'"{reasons[0]}"' in PAGE
    assert case["followup"]["eligible"] == []


def test_the_kept_flag_makes_one_checker_question_eligible_and_only_with_the_checker_on() -> None:
    case = DOC["kept"]
    answer = json.loads(case["raw_line"]["text"])
    flags, reasons = gate(answer)
    assert reasons == [] and case["gate"]["drop_reasons"] == []
    assert case["gate"]["flags"] == [f.model_dump(mode="json") for f in flags]
    assert TABLE["models"][answer["model"]][answer["feature"]]["passed"] is True
    content = load_content(ROOT)

    def ask(checker_on: bool) -> list[dict[str, Any]]:
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

    eligible = ask(True)
    assert case["followup"]["eligible"] == eligible
    assert [f["rule_id"] for f in eligible] == ["checker_flag"]
    assert eligible[0]["params"] == {"note": answer["note"], "feature": answer["feature"]}
    assert case["followup"]["with_the_checker_off"] == ask(False) == []
    # The model's note reaches the page only after "the checker noticed", never in the question.
    screen = case["followup"]["on_screen"]
    assert screen["label"] == content.locale["label.checker_noticed"] == "the checker noticed"
    assert answer["note"] not in screen["question"]
    assert f"   > {screen['label']}: {answer['note']}\n" in PAGE


def test_a_kept_flag_asks_only_on_a_feature_the_check_asks_about() -> None:
    """CRITIC_06 H02: the selector, called here on one kept flag per feature, asks nothing for a
    dug-out channel and asks for built banks; the page says so, and says what the person can do."""
    content = load_content(ROOT)
    first: dict[str, Any] = {}
    for number, line in enumerate(lines(), start=1):
        if number == 1 or not line.strip():
            continue
        a = json.loads(line)
        if "frame" not in a or a["malformed"] or a["answer"] != "yes":
            continue
        order = (a["frame"], a["model"], a["feature"], int(a["run"]))
        flags, _reasons = gate(a)
        if flags and (a["feature"] not in first or order < first[a["feature"]][0]):
            first[a["feature"]] = (order, flags)
    asks = {
        feature: bool(
            select_followups(
                {},
                SiteContext(rain="unknown"),
                None,
                flags,
                content.followups,
                form_items=content.form.get("items", []),
                checker_enabled=True,
            )
        )
        for feature, (_order, flags) in first.items()
    }
    assert asks == {"artificial_bank": True, "dug_out_channel": False}
    assert DOC["a_kept_flag_asks"] == {f: asks[f] for f in FEATURES if f in asks}
    assert (
        "So a kept flag on `dug_out_channel` makes no question eligible: `select_followups` in "
        "[`core/followups.py`](../../core/followups.py) asks only about a feature the check has "
        "an item for."
    ) in PAGE
    looked, skip = content.locale["check.looked_again"], content.locale["check.skip"]
    assert DOC["kept"]["followup"]["on_screen"]["buttons"] == [looked, skip]
    assert f'   The person taps "{looked}" or "{skip}", and no stored answer changes' in PAGE


def test_the_page_says_the_checker_is_off_live_and_credits_each_frame() -> None:
    assert footage_example.LIVE_SITE in PAGE
    for name in ("kept", "dropped"):
        row = DOC[name]["manifest_row"]
        assert (ROOT / "photos" / row["file"]).is_file()
        assert f"](../../photos/{row['file']})" in PAGE
        for key in ("source_url", "author"):
            assert row[key] and row[key] in PAGE
        # The licence as /credits writes it, not the manifest's code (critic round 15 N02).
        assert f"licence {CREDITS_NAMES[row['license']]}." in PAGE
        assert f"licence {row['license']}." not in PAGE


# How apps/web/lib/content.ts licenseName, which /credits uses, writes each manifest code.
CREDITS_NAMES = {
    "CC-BY-2.0": "CC BY 2.0",
    "CC-BY-3.0": "CC BY 3.0",
    "CC-BY-4.0": "CC BY 4.0",
    "own-CC-BY-4.0": "CC BY 4.0",
    "CC-BY-SA-2.0": "CC BY-SA 2.0",
    "CC-BY-SA-3.0": "CC BY-SA 3.0",
    "CC-BY-SA-4.0": "CC BY-SA 4.0",
    "CC0-1.0": "CC0 1.0",
    "CC0": "CC0 1.0",
    "public-domain": "Public domain",
}


def test_every_manifest_licence_is_named_the_way_credits_names_it() -> None:
    import csv

    with (ROOT / footage_example.MANIFEST).open(encoding="utf-8") as f:
        codes = {row["license"] for row in csv.DictReader(f)}
    assert codes <= set(CREDITS_NAMES), codes - set(CREDITS_NAMES)
    for code, name in CREDITS_NAMES.items():
        assert footage_example.licence_name(code) == name, code


def test_the_alt_text_says_where_each_frame_was_filmed_in_plain_english() -> None:
    # Critic round 15 N02: "filmed in United States".
    assert footage_example.place("United States") == "the United States"
    assert footage_example.place("United Kingdom") == "the United Kingdom"
    assert footage_example.place("Russia") == "Russia"
    for name in ("kept", "dropped"):
        row = DOC[name]["manifest_row"]
        where = footage_example.place(row["coarse_location"])
        assert f"a still from a creek video filmed in {where}]" in PAGE
    assert "filmed in United" not in PAGE
