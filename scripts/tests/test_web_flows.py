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
const expr = fs.readFileSync(0, "utf8");
const result = new Function("WalkFlow", "CheckFlow", "return " + expr)(WalkFlow, CheckFlow);
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
    synthetic = [w for w in walks() if w["checker_run"] != "real"]
    assert synthetic, "content/walks.yaml has no synthetic walk to hold this to"
    for w in synthetic:
        assert w["checker_dropped"] > 0
        line = checker_line(w)
        assert line == LOCALE["walk.checker_not_real"]
        assert not re.search(r"\d", line), line


def test_a_walk_from_a_real_run_shows_its_count() -> None:
    walk = {"question": None, "checker_run": "real", "checker_dropped": 4}
    assert checker_line(walk) == LOCALE["walk.checker_none"].replace("{n}", "4")


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
