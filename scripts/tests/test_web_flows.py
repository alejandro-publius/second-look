"""The walk's checker line and the rating follow-up, run from the real components.

There is no unit runner in apps/web, so Node transpiles WalkFlow.tsx and CheckFlow.tsx with the
app's own TypeScript and calls the helpers they export. Only lib/t.ts is loaded for real, reading
content/locales/en.json; every other import is an empty stand in, which is enough because the
helpers touch nothing else.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "apps" / "web"
LOCALE = json.loads((ROOT / "content" / "locales" / "en.json").read_text(encoding="utf-8"))

HARNESS = r"""
const fs = require("node:fs");
const ts = require("typescript");
const en = JSON.parse(fs.readFileSync("../../content/locales/en.json", "utf8"));
const options = {
  module: ts.ModuleKind.CommonJS,
  target: ts.ScriptTarget.ES2020,
  jsx: ts.JsxEmit.ReactJSX,
  esModuleInterop: true,
};
// An element is just its type and props, so a test can find a button and press it.
const el = (type, props) => ({ type, props });
const jsx = { jsx: el, jsxs: el, Fragment: "Fragment" };
function load(file, stubs, tail = "") {
  const src = fs.readFileSync(file, "utf8");
  const out = ts.transpileModule(src, { compilerOptions: options }).outputText + tail;
  const mod = { exports: {} };
  const req = (name) => stubs[name] ?? {};
  new Function("require", "module", "exports", out)(req, mod, mod.exports);
  return mod.exports;
}
const t = load("lib/t.ts", { "./content": { content: { locale: en } } });
const stubs = { "@/lib/t": t, "react/jsx-runtime": jsx };
const WalkFlow = load("components/WalkFlow.tsx", stubs);
// FollowupCard is not exported; the test reaches it so the buttons' wiring is checked too.
const CheckFlow = load("components/CheckFlow.tsx", stubs, "\nexports.FollowupCard = FollowupCard;");
const Text = load("lib/text.ts", {});
// The walk's city view with the content and the walks the test hands it: WalkCityView, the part
// that draws, over walks.demoCreek(), which WalkCity feeds with the walk this browser finished and
// the stored record a link names. Every Row it draws comes back as { type: "Row", props }.
function walkCityRows(content, walks, walkId) {
  const { WalkCityView } = load("components/WalkCity.tsx", {
    ...stubs,
    "@/lib/text": Text,
    "@/lib/content": content,
    "@/lib/walks": walks,
    "./FocusHeading": { FocusHeading: "FocusHeading" },
    "./ui/Row": { Row: "Row" },
  });
  const rows = [];
  const visit = (n) => {
    if (Array.isArray(n)) return n.forEach(visit);
    if (!n || typeof n !== "object") return;
    if (n.type === "Row") rows.push(n.props);
    visit(n.props && n.props.children);
  };
  visit(WalkCityView({ walk: content.walkById(walkId), demo: walks.demoCreek(), back: null }));
  return rows;
}
const expr = fs.readFileSync(0, "utf8");
const result = new Function("WalkFlow", "CheckFlow", "Text", "walkCityRows", "return " + expr)(
  WalkFlow,
  CheckFlow,
  Text,
  walkCityRows,
);
process.stdout.write(JSON.stringify(result));
"""


def run(expr: str) -> Any:
    if shutil.which("node") is None or not (WEB / "node_modules" / "typescript").exists():
        pytest.skip("needs node and apps/web/node_modules: run npm ci in apps/web")
    done = subprocess.run(
        ["node", "-e", HARNESS],
        cwd=WEB,
        input=expr,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def walks() -> list[dict[str, Any]]:
    """The walks as the web build shapes them (apps/web/scripts/build-content.mjs)."""
    raw = yaml.safe_load((ROOT / "content" / "walks.yaml").read_text(encoding="utf-8"))["walks"]
    return [
        {
            "id": w["id"],
            "question": (w.get("checker") or {}).get("question"),
            "checker_run": (w.get("checker") or {}).get("footage_run", "synthetic"),
            "checker_dropped": (w.get("checker") or {}).get("dropped", 0),
        }
        for w in raw
    ]


def checker_line(walk: dict[str, Any]) -> str:
    line = run(f"WalkFlow.checkerLine({json.dumps(walk)})")
    assert isinstance(line, str)
    return line


def test_a_walk_from_a_synthetic_run_shows_no_number() -> None:
    # Since the paid run of Sep 23 and 24 every committed walk is real, so the rule is held to any
    # synthetic walk still committed and to a made-up one: a fake run takes no flag at all
    # (scripts/build_walks.py), and the page must show no number even if a count were there.
    synthetic = [w for w in walks() if w["checker_run"] != "real"]
    for w in [*synthetic, {"question": None, "checker_run": "synthetic", "checker_dropped": 4}]:
        line = checker_line(w)
        assert line == LOCALE["walk.checker_not_real"]
        assert not re.search(r"\d", line), line


def test_a_walk_from_a_real_run_shows_its_count() -> None:
    walk = {"question": None, "checker_run": "real", "checker_dropped": 4}
    assert checker_line(walk) == LOCALE["walk.checker_none"].replace("{n}", "4")
    assert "4 of its guesses on this clip were stopped" in checker_line(walk)


def test_one_stopped_guess_was_stopped_not_were() -> None:
    # CRITIC_03 E04: live /walk/v03 read "1 of its guesses on this clip were stopped".
    line = checker_line({"question": None, "checker_run": "real", "checker_dropped": 1})
    assert line == LOCALE["walk.checker_none_one"]
    assert "1 of its guesses on this clip was stopped" in line
    assert " were " not in line


def test_a_walk_where_the_gate_stopped_nothing_does_not_blame_the_pass_rule() -> None:
    # CRITIC_03 E04: v02's build record is kept {} and dropped 0, so no model saw any feature and
    # the pass rule stopped nothing. The line said "0 of its guesses ... were stopped for that
    # reason", a reason that did not apply.
    line = checker_line({"question": None, "checker_run": "real", "checker_dropped": 0})
    assert line == LOCALE["walk.checker_nothing_seen"]
    assert "No model saw any of the four features in this clip" in line
    assert "stopped" not in line and not re.search(r"\d", line), line


def test_every_committed_walk_gets_the_line_that_fits_its_build_record() -> None:
    raw = yaml.safe_load((ROOT / "content" / "walks.yaml").read_text(encoding="utf-8"))["walks"]
    by_id = {w["id"]: w["checker"] for w in raw}
    for w in walks():
        record = by_id[w["id"]]
        line = checker_line(w)
        if record.get("question"):
            want = LOCALE["walk.checker_asked"]
        elif record.get("footage_run") != "real":
            want = LOCALE["walk.checker_not_real"]
        elif record["dropped"] == 0:
            assert record["kept"] == {}, w["id"]
            want = LOCALE["walk.checker_nothing_seen"]
        elif record["dropped"] == 1:
            want = LOCALE["walk.checker_none_one"]
        else:
            want = LOCALE["walk.checker_none"].replace("{n}", str(record["dropped"]))
        assert line == want, (w["id"], line)
    # Both cases the critic saw are among the committed walks, so both lines are held for real.
    assert {by_id[i]["dropped"] for i in ("v02", "v03")} == {0, 1}


SOURCE = (
    "OneAquaHealth Policy Brief (2026), page 9: removal of barriers. "
    "https://www.oneaquahealth.eu/app/uploads/2026/05/OneAquaHealth-Policy-Brief.pdf"
)


def test_the_reasons_then_the_source_take_one_stop_and_never_one_after_a_question() -> None:
    cases = [
        (["Pipes and drain outlets"], "Pipes and drain outlets. OneAquaHealth Policy Brief"),
        (["Built banks", "Pipes and drain outlets"], "Built banks, Pipes and drain outlets. One"),
        (["Do you see any dams?"], "Do you see any dams? OneAquaHealth Policy Brief"),
        (["Built banks", "Do you see any dams?"], "Built banks, Do you see any dams? One"),
        (["Done."], "Done. OneAquaHealth"),
        ([], "OneAquaHealth Policy Brief"),
    ]
    out = run(f"{json.dumps(cases)}.map(([r]) => Text.reasonsThenSource(r, {json.dumps(SOURCE)}))")
    for (reasons, start), line in zip(cases, out, strict=True):
        assert line.startswith(start), (reasons, line)
        assert "?." not in line and ".." not in line and "https://" not in line, line
        assert line.endswith("removal of barriers."), line


# What lib/walks.ts's exampleNeeds hands the view, stubbed: the example an honest walk ends on
# (CRITIC_09 Q01). It shows only when the walks found nothing that needs a measure.
EXAMPLE = "An example measure"
EXAMPLE_NEEDS = (
    " exampleNeeds: () => [{ sentence_id: 'x', text: "
    + json.dumps(EXAMPLE)
    + ", source: 'A source', because: ['artificial_bank'] }],"
)


def test_the_walk_city_view_names_barriers_by_a_short_label_with_one_stop_after_it() -> None:
    # CRITIC_03 E06: the walk's city view read "barriers?. OneAquaHealth Policy Brief". CRITIC_04
    # F04: it then titled the finding with the raw form question, next to "Pipes and drain
    # outlets". It now names both the finding and the reason with the short label in the locale,
    # city.finding_barriers, and the creek check still asks its own question. The real form
    # question and the real approved sentence, through the component itself.
    form = yaml.safe_load((ROOT / "content" / "form.yaml").read_text(encoding="utf-8"))
    items = [{"id": i["id"], "text": i["text"]} for i in form["items"]]
    question = next(i["text"] for i in items if i["id"] == "barriers")
    assert question.endswith("?")
    label = LOCALE["city.finding_barriers"]
    assert label and label != question and not label.endswith((".", "?", "!"))
    approved = yaml.safe_load(
        (ROOT / "content" / "approved_sentences.yaml").read_text(encoding="utf-8")
    )
    sentence = next(
        s
        for group in approved.values()
        if isinstance(group, list)
        for s in group
        if isinstance(s, dict) and s.get("id") == "city_remove_barriers"
    )
    need = {
        "sentence_id": sentence["id"],
        "text": sentence["text"],
        "because": ["barriers"],
        "source": sentence["source"],
    }
    rows = run(
        "walkCityRows("
        f"{{ content: {{ form: {{ items: {json.dumps(items)} }} }}, featureById: () => undefined,"
        " walkById: () => ({ creek_name: 'A creek' }) },"
        " { hasMeasure: (f) => f === 'barriers',"
        + EXAMPLE_NEEDS
        + " demoCreek: () => ({ visits: [{}],"
        " findings: [{ spot_id: 's', feature: 'barriers', visit_ids: ['v1'] }],"
        f" needs: [{json.dumps(need)}] }}) }},"
        " 'v02')"
    )
    # A walk that found something to fix shows no example.
    assert [r for r in rows if r.get("label") == EXAMPLE] == []
    values = [r["value"] for r in rows if r.get("label") == sentence["text"]]
    source = re.sub(r"\s*https?://\S+", "", sentence["source"]).strip()
    assert values == [f"{label}. {source}"], values
    assert "?." not in values[0]
    seen_once = LOCALE["city.walk_seen"].replace("{n}", "1")
    assert [r["label"] for r in rows if r.get("value") == seen_once] == [label]
    assert question not in json.dumps(rows, ensure_ascii=False)
    assert LOCALE["city.walk_no_measure"] not in json.dumps(rows, ensure_ascii=False)


def test_the_walk_city_view_lists_a_plant_beside_a_line_that_no_measure_answers_it() -> None:
    # CRITIC_06 H01: a walk that said yes to plants only read "Nothing was found that needs work."
    # The plant is now listed with what the checks found, and the line beside it says that none
    # of OneAquaHealth's measures answers it, which is why "what this creek needs" stays empty.
    name = "Plants that do not belong"
    rows = run(
        "walkCityRows("
        " { content: { form: { items: [] } }, featureById: (id) => ({ name: "
        + json.dumps(name)
        + " }), walkById: () => ({ creek_name: 'A creek' }) },"
        " { hasMeasure: (f) => f !== 'invasive_plant',"
        + EXAMPLE_NEEDS
        + " demoCreek: () => ({ visits: [{}],"
        " findings: [{ spot_id: 's', feature: 'invasive_plant', visit_ids: ['v1'] }],"
        " needs: [] }) },"
        " 'v02')"
    )
    # Nothing needs a measure, so the view ends on the example, marked as one (CRITIC_09 Q01).
    (example,) = [r for r in rows if r.get("label") == EXAMPLE]
    assert example["value"].endswith(". A source")
    (plant,) = [r for r in rows if r.get("label") == name]
    seen_once = LOCALE["city.walk_seen"].replace("{n}", "1")
    parts = [p for p in plant["value"]["props"]["children"] if isinstance(p, str)]
    assert parts == [seen_once, LOCALE["city.walk_no_measure"]]


def test_a_walk_whose_checker_asked_says_so() -> None:
    walk = {"question": {"feature": "f", "note": "n"}, "checker_run": "real", "checker_dropped": 0}
    assert checker_line(walk) == LOCALE["walk.checker_asked"]


def taps(first: str, *steps: Any) -> Any:
    """Every state of the rating follow-up after each tap, from the state send() leaves."""
    return run(
        "(() => { let s = { answer: undefined, finalRating: "
        + json.dumps(first)
        + ", changingRating: false }; const out = []; for (const tap of "
        + json.dumps(list(steps))
        + ") { s = CheckFlow.tapRating(s, tap, "
        + json.dumps(first)
        + "); out.push(s); } return out; })()"
    )


def test_keep_after_change_puts_the_first_rating_back_and_closes_the_picker() -> None:
    states = taps("good", "change", {"rating": "moderate"}, "keep")
    assert states[1] == {"answer": "change", "finalRating": "moderate", "changingRating": False}
    assert states[2] == {"answer": "keep", "finalRating": "good", "changingRating": False}


def test_keep_while_the_picker_is_open_closes_it() -> None:
    states = taps("good", "change", "keep")
    assert states[0]["changingRating"] is True
    assert states[1] == {"answer": "keep", "finalRating": "good", "changingRating": False}


def test_change_then_a_rating_is_what_the_record_carries() -> None:
    # The path check.spec.ts drives: Change, then Moderate, then Finish.
    states = taps("good", "change", {"rating": "moderate"})
    assert states[-1] == {"answer": "change", "finalRating": "moderate", "changingRating": False}


CARD = """(() => {
  const taps = [];
  const answers = [];
  const tree = CheckFlow.FollowupCard({
    followup: { rule_id: "rating_check", kind: "keep_rating", question_text: "q" },
    value: "change",
    onAnswer: (v) => answers.push(v),
    photos: [],
    onPhotos: () => {},
    changingRating: true,
    ratingOptions: [{ id: "moderate", label: "Moderate", value: "moderate" }],
    finalRating: "moderate",
    onRatingTap: (tap) => taps.push(tap),
  });
  const buttons = [];
  (function walk(n) {
    if (Array.isArray(n)) return n.forEach(walk);
    if (n && typeof n === "object" && n.props) {
      if (n.type === "button") buttons.push(n);
      walk(n.props.children);
    }
  })(tree);
  for (const b of buttons) b.props.onClick();
  return { labels: buttons.map((b) => b.props.children), taps, answers };
})()"""


def test_the_rating_buttons_go_through_tap_rating() -> None:
    # Keep once went to onAnswer alone, which left the changed rating in place.
    got = run(CARD)
    labels = [LOCALE["check.keep_rating"], LOCALE["check.change_rating"], "Moderate"]
    assert got["labels"] == labels
    assert got["taps"] == ["keep", "change", {"rating": "moderate"}]
    assert got["answers"] == []
