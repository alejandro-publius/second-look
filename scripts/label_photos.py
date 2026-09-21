"""Local pages for two jobs: labelling photos blind, and placing marks on lesson photos.

Blind labelling: uv run python scripts/label_photos.py --name rachel --roles test,practice,lesson
It prints a http://127.0.0.1:<random port>/ link. The page shows one photo at a time with the
feature question from content/features.yaml and three buttons: present, absent, ambiguous.
Labels go to labels_<name>.csv in the repo root (gitignored). The page never opens, reads or
shows another labeller's file, and never shows the manifest's gold_label, notes or scene.

Marking: uv run python scripts/label_photos.py --marks
The page shows one lesson photo at a time. Alex clicks where a mark goes and types a label of
five words or fewer. Saving writes the x and y fractions and the label into the lesson YAML, into
that pair's marks or into practice_marks. Every mark written here carries approved: false,
because only Rachel approves a mark, and preflight blocks launch while one is unapproved.
"""

from __future__ import annotations

import argparse
import copy
import csv
import html
import json
import re
import sys
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import yaml

ROOT = Path(__file__).resolve().parents[1]
NAME_RE = re.compile(r"^[a-z0-9]{1,20}$")
LABELS = ("present", "absent", "ambiguous")
LABEL_COLUMNS = ["photo_id", "feature", "label", "labelled_at_utc"]
DEFAULT_ROLES = ("test", "practice", "lesson")
MAX_LABEL_WORDS = 5
MARK_PLACES = 4  # four decimals is finer than any screen, and keeps the YAML line short


def labels_path(root: Path, name: str) -> Path:
    return root / f"labels_{name}.csv"


class LabelStore:
    """Read and write exactly one labels file."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.rows: dict[str, dict[str, str]] = {}
        if path.exists():
            with path.open(newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    self.rows[row["photo_id"]] = dict(row)

    def set(self, photo_id: str, feature: str, label: str) -> None:
        if label not in LABELS:
            raise ValueError(f"label must be one of {LABELS}")
        self.rows[photo_id] = {
            "photo_id": photo_id,
            "feature": feature,
            "label": label,
            "labelled_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        with self.path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=LABEL_COLUMNS)
            w.writeheader()
            for pid in sorted(self.rows):
                w.writerow({c: self.rows[pid].get(c, "") for c in LABEL_COLUMNS})


def load_queue(root: Path, roles: tuple[str, ...]) -> list[dict[str, str]]:
    """Photos to label: id, file and feature only. Gold labels and notes are not read."""
    with (root / "photos" / "manifest.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    queue = [
        {"id": r["id"], "file": r["file"], "feature": r["feature"]}
        for r in rows
        if r["role"] in roles and r["feature"]
    ]
    return sorted(queue, key=lambda r: r["id"])


def load_questions(root: Path) -> dict[str, dict[str, str]]:
    with (root / "content" / "features.yaml").open(encoding="utf-8") as f:
        features = yaml.safe_load(f).get("features", [])
    return {f["id"]: {"name": f["name"], "question": f["question"]} for f in features}


def render(
    queue: list[dict[str, str]],
    store: LabelStore,
    questions: dict[str, dict[str, str]],
    name: str,
    photo_id: str | None,
) -> str:
    done = [p for p in queue if p["id"] in store.rows]
    todo = [p for p in queue if p["id"] not in store.rows]
    current = next((p for p in queue if p["id"] == photo_id), None) if photo_id else None
    if current is None:
        current = todo[0] if todo else None
    head = (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>Label photos: {html.escape(name)}</title>"
        "<style>body{font-family:system-ui;max-width:52rem;margin:1rem auto;padding:0 1rem}"
        "img{max-width:100%;height:auto;border:1px solid #888}"
        "button{font-size:1.25rem;padding:.75rem 1.5rem;margin:.5rem .5rem .5rem 0;min-width:9rem}"
        ".muted{color:#555}</style></head><body>"
    )
    parts = [head, f"<h1>Labelling as {html.escape(name)}</h1>"]
    parts.append(
        f"<p class='muted'>{len(done)} of {len(queue)} labelled. "
        f"Your labels go to {html.escape(store.path.name)} and nowhere else.</p>"
    )
    if current is None:
        parts.append("<p><strong>All done.</strong> Close this tab and run merge_labels.py.</p>")
    else:
        q = questions.get(current["feature"], {"name": current["feature"], "question": ""})
        parts.append(f"<h2>{html.escape(q['name'])}</h2>")
        parts.append(f"<p><strong>{html.escape(q['question'])}</strong></p>")
        parts.append(
            f"<p><img src='/photo/{html.escape(current['id'])}' alt='Creek photo to label'></p>"
        )
        parts.append("<form method='post' action='/label'>")
        parts.append(f"<input type='hidden' name='photo_id' value='{html.escape(current['id'])}'>")
        for label in LABELS:
            parts.append(f"<button type='submit' name='label' value='{label}'>{label}</button>")
        parts.append("</form>")
        parts.append(f"<p class='muted'>Photo id {html.escape(current['id'])}</p>")
    if done:
        links = " ".join(
            f"<a href='/?photo={html.escape(p['id'])}'>{html.escape(p['id'])}</a>" for p in done
        )
        parts.append(f"<p class='muted'>Change a label: {links}</p>")
    parts.append("</body></html>")
    return "".join(parts)


class LocalPage(BaseHTTPRequestHandler):
    """Shared plumbing for both local pages. Nothing here reaches the network."""

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return  # quiet; nothing here is worth logging

    def _send(self, status: HTTPStatus, body: bytes, ctype: str = "text/html") -> None:
        self.send_response(status)
        self.send_header("Content-Type", f"{ctype}; charset=utf-8" if "text" in ctype else ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def make_server(
    root: Path, name: str, roles: tuple[str, ...] = DEFAULT_ROLES, port: int = 0
) -> ThreadingHTTPServer:
    if not NAME_RE.match(name):
        raise SystemExit("name must be 1 to 20 lowercase letters or digits, for example rachel")
    root = root.resolve()
    queue = load_queue(root, roles)
    questions = load_questions(root)
    store = LabelStore(labels_path(root, name))
    by_id = {p["id"]: p for p in queue}

    class Handler(LocalPage):
        def do_GET(self) -> None:  # noqa: N802
            url = urlparse(self.path)
            if url.path == "/":
                chosen = parse_qs(url.query).get("photo", [None])[0]
                page = render(queue, store, questions, name, chosen)
                self._send(HTTPStatus.OK, page.encode("utf-8"))
                return
            if url.path.startswith("/photo/"):
                photo = by_id.get(url.path[len("/photo/") :])
                if photo is None:
                    self._send(HTTPStatus.NOT_FOUND, b"no such photo", "text/plain")
                    return
                file = (root / "photos" / photo["file"]).resolve()
                if root / "photos" not in file.parents or not file.is_file():
                    self._send(HTTPStatus.NOT_FOUND, b"no such file", "text/plain")
                    return
                ctype = "image/png" if file.suffix.lower() == ".png" else "image/jpeg"
                self._send(HTTPStatus.OK, file.read_bytes(), ctype)
                return
            self._send(HTTPStatus.NOT_FOUND, b"not found", "text/plain")

        def do_POST(self) -> None:  # noqa: N802
            if urlparse(self.path).path != "/label":
                self._send(HTTPStatus.NOT_FOUND, b"not found", "text/plain")
                return
            length = int(self.headers.get("Content-Length") or 0)
            form = parse_qs(self.rfile.read(length).decode("utf-8"))
            photo_id = form.get("photo_id", [""])[0]
            label = form.get("label", [""])[0]
            photo = by_id.get(photo_id)
            if photo is None or label not in LABELS:
                self._send(HTTPStatus.BAD_REQUEST, b"unknown photo or label", "text/plain")
                return
            store.set(photo_id, photo["feature"], label)
            self.send_response(HTTPStatus.SEE_OTHER)
            self.send_header("Location", "/")
            self.end_headers()

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


# ---------------------------------------------------------------- marking mode


class MarkError(Exception):
    """Something a person can fix: a long label, a number out of range, an unsafe write."""


@dataclass(frozen=True)
class MarkTarget:
    """One lesson photo, and the one place in the lesson file where its marks live."""

    feature: str
    photo_id: str
    kind: str  # "pair" or "practice"
    pair: int  # index into contrast_pairs, or -1 for the practice photo

    @property
    def where(self) -> str:
        if self.kind == "practice":
            return "practice_marks"
        return f"contrast pair {self.pair + 1} marks"


def lesson_path(root: Path, feature: str) -> Path:
    return root / "content" / "lessons" / f"{feature}.yaml"


def load_lesson(path: Path) -> dict[str, Any]:
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    return doc if isinstance(doc, dict) else {}


def load_mark_targets(root: Path) -> list[MarkTarget]:
    """Every lesson photo that can carry marks, in lesson file order.

    Marks sit on the actual photo of a pair, never on the assume photo, which is the one the
    lesson asks people to read wrongly first.
    """
    targets: list[MarkTarget] = []
    for path in sorted((root / "content" / "lessons").glob("*.yaml")):
        doc = load_lesson(path)
        feature = str(doc.get("feature") or path.stem)
        for i, pair in enumerate(doc.get("contrast_pairs") or []):
            photo_id = str((pair or {}).get("actual_photo_id") or "")
            if photo_id:
                targets.append(MarkTarget(feature, photo_id, "pair", i))
        practice_id = str((doc.get("practice") or {}).get("photo_id") or "")
        if practice_id:
            targets.append(MarkTarget(feature, practice_id, "practice", -1))
    return targets


def read_marks(doc: dict[str, Any], target: MarkTarget) -> list[dict[str, Any]]:
    """The marks already in the file for this photo."""
    if target.kind == "practice":
        raw = doc.get("practice_marks") or []
    else:
        pairs = doc.get("contrast_pairs") or []
        raw = (pairs[target.pair] or {}).get("marks") or [] if target.pair < len(pairs) else []
    return [dict(m) for m in raw if isinstance(m, dict)]


def iter_marks(lesson: dict[str, Any]) -> Iterator[tuple[str, dict[str, Any]]]:
    """Every mark in one lesson, with a short word for where it sits. Preflight reads this."""
    for i, pair in enumerate(lesson.get("contrast_pairs") or [], 1):
        for mark in (pair or {}).get("marks") or []:
            if isinstance(mark, dict):
                yield f"pair {i}", mark
    for mark in lesson.get("practice_marks") or []:
        if isinstance(mark, dict):
            yield "practice", mark


def label_problem(label: str) -> str | None:
    """Why this label cannot go on a mark, or None if it can."""
    words = label.split()
    if not words:
        return "a mark needs a label"
    if len(words) > MAX_LABEL_WORDS:
        return (
            f"label has {len(words)} words: use {MAX_LABEL_WORDS} words or fewer, "
            f"because the dot list has to fit under a phone photo"
        )
    if "\n" in label:
        return "a label is one line"
    return None


def clean_marks(raw: Any) -> list[dict[str, Any]]:
    """Check what the page sent. Raises MarkError with a line a person can act on."""
    if not isinstance(raw, list):
        raise MarkError("marks must be a list")
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            raise MarkError("each mark is an object with x, y and label")
        try:
            x, y = float(item["x"]), float(item["y"])
        except (KeyError, TypeError, ValueError):
            raise MarkError("each mark needs a number x and a number y") from None
        if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
            raise MarkError("x and y are fractions of the photo, so they sit between 0 and 1")
        label = str(item.get("label", "")).strip()
        problem = label_problem(label)
        if problem:
            raise MarkError(problem)
        out.append(
            {
                "x": round(x, MARK_PLACES),
                "y": round(y, MARK_PLACES),
                "label": label,
                "approved": False,
            }
        )
    return out


def _mark_key(mark: dict[str, Any]) -> tuple[float, float, str]:
    return (
        round(float(mark.get("x", 0)), MARK_PLACES),
        round(float(mark.get("y", 0)), MARK_PLACES),
        str(mark.get("label", "")),
    )


def merge_approved(old: list[dict[str, Any]], new: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """A mark that has not moved and has the same label keeps the approval Rachel gave it.

    Anything moved, renamed or added is new work, so it goes back to approved: false.
    """
    kept = {_mark_key(m): m.get("approved") is True for m in old}
    return [{**m, "approved": kept.get(_mark_key(m), False)} for m in new]


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _value_block(lines: list[str], key_line: int) -> tuple[int, int]:
    """The half open line range holding the value written under the key on key_line."""
    indent = _indent(lines[key_line])
    start = end = key_line + 1
    i = start
    while i < len(lines):
        if lines[i].strip():
            if _indent(lines[i]) <= indent:
                break
            end = i + 1
        i += 1
    return start, end


def _top_key_line(lines: list[str], key: str) -> int | None:
    for i, line in enumerate(lines):
        if _indent(line) == 0 and ":" in line and line.split(":", 1)[0].strip() == key:
            return i
    return None


def _pair_spans(lines: list[str]) -> list[tuple[int, int]]:
    """The line range of each contrast pair, so a write lands in the right pair."""
    head = _top_key_line(lines, "contrast_pairs")
    if head is None:
        return []
    start, end = _value_block(lines, head)
    body = [i for i in range(start, end) if lines[i].strip()]
    if not body:
        return []
    dash = _indent(lines[body[0]])
    starts = [
        i for i in body if _indent(lines[i]) == dash and lines[i].lstrip().startswith(("- ", "-\t"))
    ]
    return [(s, starts[n + 1] if n + 1 < len(starts) else end) for n, s in enumerate(starts)]


def _marks_key_line(lines: list[str], span: tuple[int, int]) -> int | None:
    s, e = span
    dash = _indent(lines[s])
    for i in range(s, e):
        line = lines[i]
        if _indent(line) > dash and ":" in line and line.split(":", 1)[0].strip() == "marks":
            return i
    return None


def _num(value: float) -> str:
    """A fraction that always reads as a float, so the YAML type never flips to int."""
    text = f"{round(float(value), MARK_PLACES):.{MARK_PLACES}f}".rstrip("0")
    return text + "0" if text.endswith(".") else text


def _mark_line(indent: int, mark: dict[str, Any]) -> str:
    label = json.dumps(str(mark["label"]), ensure_ascii=False)
    approved = "true" if mark.get("approved") is True else "false"
    return (
        f"{' ' * indent}- {{ x: {_num(mark['x'])}, y: {_num(mark['y'])}, "
        f"label: {label}, approved: {approved} }}"
    )


def _splice(
    lines: list[str], key_line: int, name: str, indent: int, marks: list[dict[str, Any]]
) -> tuple[list[str], list[str]]:
    start, end = _value_block(lines, key_line)
    dropped = [ln for ln in lines[start:end] if ln.lstrip().startswith("#")]
    head = f"{' ' * indent}{name}:"
    block = [head, *(_mark_line(indent + 2, m) for m in marks)] if marks else [f"{head} []"]
    return [*lines[:key_line], *block, *lines[end:]], dropped


def plan_write(text: str, target: MarkTarget, marks: list[dict[str, Any]]) -> tuple[str, list[str]]:
    """The new file text, and any comment lines this write would drop.

    Only the marks lines are rewritten. Every other line, comments included, is copied across
    byte for byte, because Rachel reads the comments in these files.
    """
    lines = text.splitlines()
    if target.kind == "practice":
        name, indent = "practice_marks", 0
        key_line = _top_key_line(lines, name)
        if key_line is None:
            lines = [*lines, f"{name}:"]
            key_line = len(lines) - 1
    else:
        spans = _pair_spans(lines)
        if not 0 <= target.pair < len(spans):
            raise MarkError(f"no contrast pair {target.pair + 1} in this lesson file")
        span = spans[target.pair]
        name = "marks"
        found = _marks_key_line(lines, span)
        if found is None:
            indent = _indent(lines[span[0]]) + 2
            at = span[1]
            while at > span[0] and not lines[at - 1].strip():
                at -= 1
            lines = [*lines[:at], f"{' ' * indent}{name}:", *lines[at:]]
            key_line = at
        else:
            key_line, indent = found, _indent(lines[found])
    new_lines, dropped = _splice(lines, key_line, name, indent, marks)
    return "\n".join(new_lines) + "\n", dropped


def _without_marks(doc: dict[str, Any], target: MarkTarget) -> dict[str, Any]:
    """The lesson with this photo's marks taken out, so the rest can be compared."""
    other = copy.deepcopy(doc)
    if target.kind == "practice":
        other.pop("practice_marks", None)
    else:
        pairs = other.get("contrast_pairs") or []
        if target.pair < len(pairs) and isinstance(pairs[target.pair], dict):
            pairs[target.pair].pop("marks", None)
    return other


def write_marks(
    path: Path,
    target: MarkTarget,
    marks: list[dict[str, Any]],
    say: Callable[[str], None] = print,
) -> list[dict[str, Any]]:
    """Put marks into the lesson file and return what landed there.

    The file is only written once the new text parses and says exactly what it should say,
    so a bad write cannot leave Rachel with a broken lesson.
    """
    text = path.read_text(encoding="utf-8")
    before = load_lesson(path)
    merged = merge_approved(read_marks(before, target), marks)
    new_text, dropped = plan_write(text, target, merged)
    for line in dropped:
        say(f"warning: this write drops a comment from {path.name}: {line.strip()}")
    try:
        after = yaml.safe_load(new_text)
    except yaml.YAMLError as e:
        raise MarkError(f"the new {path.name} would not parse, so nothing was written: {e}") from e
    if not isinstance(after, dict):
        raise MarkError(f"the new {path.name} is not a lesson, so nothing was written")
    landed = read_marks(after, target)
    if [_mark_key(m) for m in landed] != [_mark_key(m) for m in merged]:
        raise MarkError(f"the marks did not land in {target.where}, so nothing was written")
    if _without_marks(before, target) != _without_marks(after, target):
        raise MarkError(f"the write would change the rest of {path.name}, so nothing was written")
    path.write_text(new_text, encoding="utf-8")
    return landed


MARKS_HELP = (
    "Click the photo where a mark goes, type up to five words, then Add mark. "
    "Save writes the lesson file. Every mark is written with approved: false, "
    "because Rachel is the one who approves a mark."
)

MARKS_STYLE = (
    "body{font-family:system-ui;max-width:60rem;margin:1rem auto;padding:0 1rem}"
    "#frame{position:relative;display:inline-block;max-width:100%}"
    "#photo{display:block;width:44rem;max-width:100%;height:auto;border:1px solid #888;"
    "cursor:crosshair}"
    ".dot{position:absolute;width:1.6rem;height:1.6rem;margin:-.8rem 0 0 -.8rem;border-radius:50%;"
    "background:#b3121b;color:#fff;font:700 .95rem/1.6rem system-ui;text-align:center}"
    "button{font-size:1.05rem;padding:.5rem 1rem;margin:.25rem .5rem .25rem 0}"
    "input{font-size:1.05rem;padding:.5rem;width:22rem;max-width:100%}"
    ".muted{color:#555}.warn{color:#8a1c00;font-weight:700}"
    "li{margin:.35rem 0}"
)

MARKS_SCRIPT = """
(function () {
  var state = JSON.parse(document.getElementById('state').textContent);
  var frame = document.getElementById('frame');
  var photo = document.getElementById('photo');
  var list = document.getElementById('list');
  var msg = document.getElementById('msg');
  var box = document.getElementById('label');
  var addBtn = document.getElementById('add');
  var marks = state.marks;
  var pending = null;

  function say(text, bad) {
    msg.textContent = text;
    msg.className = bad ? 'warn' : 'muted';
  }

  function dot(point, text) {
    var el = document.createElement('span');
    el.className = 'dot';
    el.textContent = text;
    el.style.left = (point.x * 100) + '%';
    el.style.top = (point.y * 100) + '%';
    frame.appendChild(el);
  }

  function draw() {
    var old = frame.querySelectorAll('.dot');
    for (var i = 0; i < old.length; i++) { old[i].remove(); }
    marks.forEach(function (m, i) { dot(m, String(i + 1)); });
    if (pending) { dot(pending, '?'); }
    list.textContent = '';
    marks.forEach(function (m, i) {
      var li = document.createElement('li');
      li.appendChild(document.createTextNode(
        m.label + (m.approved ? ' (approved)' : ' (waiting for Rachel)') + ' '));
      var b = document.createElement('button');
      b.textContent = 'Remove';
      b.addEventListener('click', function () { marks.splice(i, 1); draw(); });
      li.appendChild(b);
      list.appendChild(li);
    });
  }

  photo.addEventListener('click', function (e) {
    var r = photo.getBoundingClientRect();
    pending = { x: (e.clientX - r.left) / r.width, y: (e.clientY - r.top) / r.height };
    box.disabled = false;
    addBtn.disabled = false;
    box.value = '';
    box.focus();
    say('Type a label of ' + state.max_words + ' words or fewer, then Add mark.');
    draw();
  });

  function add() {
    if (!pending) { say('Click the photo first.', true); return; }
    var label = box.value.trim();
    var words = label.split(/\\s+/).filter(Boolean);
    if (words.length === 0) { say('A mark needs a label.', true); return; }
    if (words.length > state.max_words) {
      say('Label has ' + words.length + ' words. Use ' + state.max_words
          + ' words or fewer.', true);
      return;
    }
    marks.push({ x: pending.x, y: pending.y, label: label, approved: false });
    pending = null;
    box.value = '';
    box.disabled = true;
    addBtn.disabled = true;
    say('Mark added. Save when this photo is done.');
    draw();
  }

  addBtn.addEventListener('click', add);
  box.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') { e.preventDefault(); add(); }
  });

  document.getElementById('save').addEventListener('click', function () {
    var body = new URLSearchParams({
      photo_id: state.photo_id, marks: JSON.stringify(marks) });
    fetch('/marks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: body
    }).then(function (r) {
      return r.text().then(function (t) { say(t, r.status !== 200); });
    }).catch(function (err) { say(String(err), true); });
  });

  draw();
})();
"""


def render_marks(
    targets: list[MarkTarget], current: MarkTarget, marks: list[dict[str, Any]], note: str = ""
) -> str:
    """The marking page for one lesson photo."""
    n = targets.index(current) + 1
    state = {
        "photo_id": current.photo_id,
        "marks": [
            {
                "x": round(float(m.get("x", 0)), MARK_PLACES),
                "y": round(float(m.get("y", 0)), MARK_PLACES),
                "label": str(m.get("label", "")),
                "approved": m.get("approved") is True,
            }
            for m in marks
        ],
        "max_words": MAX_LABEL_WORDS,
    }
    # A lone "<" inside a script block would end it early, so it is written as an escape.
    state_json = json.dumps(state, ensure_ascii=False).replace("<", "\\u003c")
    links = " ".join(
        f"<a href='/?photo={html.escape(t.photo_id)}'>{'*' if t is current else ''}"
        f"{html.escape(t.photo_id)}</a>"
        for t in targets
    )
    parts = [
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width, initial-scale=1'>",
        f"<title>Place marks: {html.escape(current.feature)}</title>",
        f"<style>{MARKS_STYLE}</style></head><body>",
        f"<h1>Place marks: {html.escape(current.feature)}</h1>",
        f"<p class='muted'>Photo {n} of {len(targets)}. "
        f"{html.escape(current.photo_id)}. These marks go into "
        f"content/lessons/{html.escape(current.feature)}.yaml under "
        f"{html.escape(current.where)}.</p>",
        f"<p class='muted'>{html.escape(MARKS_HELP)}</p>",
        "<div id='frame'>",
        f"<img id='photo' src='/photo/{html.escape(current.photo_id)}' "
        "alt='Lesson photo. Click where a mark goes.'>",
        "</div>",
        "<p><label for='label'>Label for the new mark</label><br>",
        "<input id='label' maxlength='80' disabled></p>",
        "<p><button id='add' disabled>Add mark</button>",
        "<button id='save'>Save to the lesson file</button></p>",
        f"<p id='msg' role='status' class='muted'>{html.escape(note)}</p>",
        "<ol id='list'></ol>",
        f"<p class='muted'>Photos: {links}</p>",
        f"<script id='state' type='application/json'>{state_json}</script>",
        f"<script>{MARKS_SCRIPT}</script>",
        "</body></html>",
    ]
    return "".join(parts)


def load_photo_files(root: Path) -> dict[str, str]:
    """Photo id to file path, for the photos the marking page is allowed to show."""
    with (root / "photos" / "manifest.csv").open(newline="", encoding="utf-8") as f:
        return {r["id"]: r["file"] for r in csv.DictReader(f)}


def make_marks_server(root: Path, port: int = 0) -> ThreadingHTTPServer:
    root = root.resolve()
    targets = load_mark_targets(root)
    if not targets:
        raise SystemExit("no lesson photos to mark: content/lessons is empty")
    files = load_photo_files(root)
    by_photo = {t.photo_id: t for t in targets}

    def marks_of(target: MarkTarget) -> list[dict[str, Any]]:
        return read_marks(load_lesson(lesson_path(root, target.feature)), target)

    class Handler(LocalPage):
        def do_GET(self) -> None:  # noqa: N802
            url = urlparse(self.path)
            if url.path == "/":
                chosen = parse_qs(url.query).get("photo", [""])[0]
                current = by_photo.get(chosen, targets[0])
                note = parse_qs(url.query).get("note", [""])[0]
                page = render_marks(targets, current, marks_of(current), note)
                self._send(HTTPStatus.OK, page.encode("utf-8"))
                return
            if url.path.startswith("/photo/"):
                photo_id = url.path[len("/photo/") :]
                name = files.get(photo_id) if photo_id in by_photo else None
                if name is None:
                    self._send(HTTPStatus.NOT_FOUND, b"no such lesson photo", "text/plain")
                    return
                file = (root / "photos" / name).resolve()
                if root / "photos" not in file.parents or not file.is_file():
                    self._send(HTTPStatus.NOT_FOUND, b"no such file", "text/plain")
                    return
                ctype = "image/png" if file.suffix.lower() == ".png" else "image/jpeg"
                self._send(HTTPStatus.OK, file.read_bytes(), ctype)
                return
            self._send(HTTPStatus.NOT_FOUND, b"not found", "text/plain")

        def do_POST(self) -> None:  # noqa: N802
            if urlparse(self.path).path != "/marks":
                self._send(HTTPStatus.NOT_FOUND, b"not found", "text/plain")
                return
            length = int(self.headers.get("Content-Length") or 0)
            form = parse_qs(self.rfile.read(length).decode("utf-8"))
            target = by_photo.get(form.get("photo_id", [""])[0])
            if target is None:
                self._send(HTTPStatus.BAD_REQUEST, b"unknown lesson photo", "text/plain")
                return
            try:
                marks = clean_marks(json.loads(form.get("marks", ["[]"])[0]))
                landed = write_marks(lesson_path(root, target.feature), target, marks)
            except (MarkError, json.JSONDecodeError, OSError) as e:
                self._send(HTTPStatus.BAD_REQUEST, str(e).encode("utf-8"), "text/plain")
                return
            waiting = sum(1 for m in landed if m.get("approved") is not True)
            body = (
                f"Saved {len(landed)} marks to content/lessons/{target.feature}.yaml "
                f"under {target.where}. {waiting} wait for Rachel to approve them."
            )
            self._send(HTTPStatus.OK, body.encode("utf-8"), "text/plain")

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--name", help="your first name, lowercase (blind labelling)")
    parser.add_argument("--roles", default=",".join(DEFAULT_ROLES), help="comma separated roles")
    parser.add_argument(
        "--marks", action="store_true", help="place marks on lesson photos instead of labelling"
    )
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.marks:
        server = make_marks_server(args.root)
        host, port = str(server.server_address[0]), int(server.server_address[1])
        print(f"marks page: http://{host}:{port}/  (Ctrl-C to stop)")
        print("marks are written into content/lessons/*.yaml with approved: false")
    else:
        if not args.name:
            parser.error("--name is required, or use --marks to place marks on lesson photos")
        roles = tuple(r.strip() for r in args.roles.split(",") if r.strip())
        server = make_server(args.root, args.name, roles)
        host, port = str(server.server_address[0]), int(server.server_address[1])
        print(f"label page for {args.name}: http://{host}:{port}/  (Ctrl-C to stop)")
        print(f"labels are written to {labels_path(args.root.resolve(), args.name)}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
