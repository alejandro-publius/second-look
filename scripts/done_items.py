"""The item checks behind docs/internal/DONE.md that need more than a line of shell.

Each check reads the repo (and, for a few, the live site or a file on this Mac) and prints what is
missing. It exits 0 only when nothing is. Nothing here writes anywhere.

  uv run python scripts/done_items.py readme-order
  uv run python scripts/done_items.py --list

Results measured by the hardening scripts must be fresh: measured at a commit that contains
BASE_COMMIT, the tip of depth when UPDATE_27's work began, or after that commit's time for a file
that records a time and no commit. An older file measured a different README and a different site.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import yaml
from PIL import Image

from core.lock import DATA_LOCK_UTC
from scripts import done_check

ROOT = Path(__file__).resolve().parents[1]
BASE_COMMIT = "8cecc38"
LIVE = "https://second-look-79t.pages.dev"
SCREEN_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
IMAGE_SUFFIXES = SCREEN_SUFFIXES | {".gif"}
SCREEN_MAX_BYTES = 400_000
GIF_MAX_BYTES = 3_000_000
SOCIAL_SIZE = (1280, 640)
SOCIAL_MAX_BYTES = 1_000_000  # GitHub refuses a social preview of 1 MB or more
# The screens inside /t. The route itself is the test flow, so its slug alone names nothing.
FLOW_SCREENS = ("consent", "warmup", "lesson", "item", "score")
FIVE_VERBS = ("train", "check", "verify", "record", "act")
FHIR_TYPES = (
    "Observation",
    "Location",
    "Practitioner",
    "PractitionerRole",
    "QuestionnaireResponse",
    "Questionnaire",
    "Provenance",
    "Bundle",
    "Organization",
    "Library",
    "ServiceRequest",
    "Specimen",
    "Media",
)
WALK_SKIP = {".git", "node_modules", ".venv", ".next", "out", "__pycache__", ".mypy_cache"}
AUDIO_SUFFIXES = {".wav", ".m4a", ".aiff", ".aif", ".mp3", ".caf", ".flac"}
VOICE_MIN_SECONDS = 120.0
LOW_SEVERITY = {"none", "cosmetic"}
SUBMIT_ALLOWED = {"video_link", "repo_public"}
DEVPOST_RE = re.compile(r"https://devpost\.com/software/[A-Za-z0-9-]+")

Check = Callable[[Path], list[str]]
Fetch = Callable[[str], tuple[int, str]]


# ---------------------------------------------------------------------------------------------
# Reading Markdown


@dataclass(frozen=True)
class Heading:
    line: int
    level: int
    title: str


FENCE = re.compile(r"^\s*(```|~~~)")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
IMG_MD = re.compile(r"!\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
IMG_HTML = re.compile(r"<img\b[^>]*\bsrc=[\"']([^\"']+)[\"']", re.I)
LINK_MD = re.compile(r"(?<![!\]])\[[^\]\[]+\]\(([^)\s]+)")
BACKTICKED = re.compile(r"`([^`\n]+)`")
TABLE_SEP = re.compile(r"^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?$")
MARKER = re.compile(r"<!--\s*claim:|<!--v:")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def headings(lines: list[str]) -> list[Heading]:
    found: list[Heading] = []
    fenced = False
    for n, line in enumerate(lines):
        if FENCE.match(line):
            fenced = not fenced
            continue
        m = None if fenced else HEADING.match(line)
        if m:
            found.append(Heading(n, len(m.group(1)), m.group(2)))
    return found


def section(lines: list[str], pattern: str, after: int = -1) -> tuple[Heading, list[str]] | None:
    """The first heading after line `after` whose title matches, and its body."""
    hs = headings(lines)
    for i, h in enumerate(hs):
        if h.line > after and re.search(pattern, h.title, re.I):
            end = next((g.line for g in hs[i + 1 :] if g.level <= h.level), len(lines))
            return h, lines[h.line + 1 : end]
    return None


def tables(lines: list[str]) -> list[list[list[str]]]:
    """Every table in the lines: its rows as cells, the separator row left out."""
    found: list[list[list[str]]] = []
    current: list[list[str]] = []
    for line in [*lines, ""]:
        s = line.strip()
        if s.startswith("|"):
            if not TABLE_SEP.fullmatch(s):
                current.append(done_check.split_row(s))
            continue
        if current:
            found.append(current)
            current = []
    return found


def list_items(lines: list[str], numbered_only: bool = False) -> list[str]:
    """Top level list items, each with its continuation lines."""
    start = re.compile(r"^(\d+)\.\s+" if numbered_only else r"^(\d+\.|[-*])\s+")
    items: list[str] = []
    for line in lines:
        if start.match(line):
            items.append(line)
        elif items and line.startswith((" ", "\t")) and line.strip():
            items[-1] += " " + line.strip()
        elif not line.strip() and items:
            items.append("")
    return [i for i in items if i]


def images(text: str) -> list[str]:
    return [m.group(1) for m in IMG_MD.finditer(text)] + [
        m.group(1) for m in IMG_HTML.finditer(text)
    ]


def local(root: Path, src: str) -> Path | None:
    """The file a relative link points at, or None for a link off the repo."""
    if re.match(r"^[a-z]+:", src) or src.startswith("//"):
        return None
    return root / src.split("#")[0].split("?")[0].lstrip("/")


def tokens(name: str) -> list[str]:
    return [t for t in re.split(r"[^a-z0-9]+", name.lower()) if t]


def names(stem: str, slug: str) -> bool:
    """True when the file name holds the slug as whole words; warm-up and warmup both count."""
    want = "".join(tokens(slug))
    words = tokens(stem)
    return any(
        "".join(words[i : i + n]) == want for n in range(1, 4) for i in range(len(words) - n + 1)
    )


# ---------------------------------------------------------------------------------------------
# Freshness


def commit_problem(root: Path, sha: str | None, what: str) -> str | None:
    """None when the commit contains BASE_COMMIT, else why the file counts as stale."""
    if not sha:
        return f"{what} names no commit it was measured at"
    proc = subprocess.run(
        ["git", "merge-base", "--is-ancestor", BASE_COMMIT, sha],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0:
        return None
    if proc.returncode == 1:
        return f"{what} was measured at {sha}, before {BASE_COMMIT}; measure it again"
    return f"{what} names commit {sha}, which this clone does not have"


def base_time(root: Path) -> datetime:
    out = subprocess.run(
        ["git", "show", "-s", "--format=%ct", BASE_COMMIT],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    return datetime.fromtimestamp(int(out), tz=UTC)


def parse_utc(text: object) -> datetime | None:
    if not isinstance(text, str):
        return None
    try:
        when = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return when if when.tzinfo else when.replace(tzinfo=UTC)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def results_file(root: Path, name: str) -> tuple[dict[str, Any] | None, list[str]]:
    rel = f"results/harden/{name}"
    doc = load_json(root / rel)
    if not isinstance(doc, dict):
        return None, [f"{rel} is missing or is not JSON"]
    problem = commit_problem(root, doc.get("commit"), rel)
    return doc, [problem] if problem else []


# ---------------------------------------------------------------------------------------------
# Block 23: the repo lift


def route_slugs(root: Path) -> set[str]:
    app = root / "apps" / "web" / "app"
    slugs: set[str] = set()
    for page in app.rglob("page.tsx"):
        parts = [p for p in page.parent.relative_to(app).parts if not p.startswith(("[", "(", "_"))]
        slug = "-".join(parts) or "landing"
        if slug != "t":
            slugs.add(slug)
    return slugs


def check_screens(root: Path) -> list[str]:
    folder = root / "docs" / "screens"
    if not folder.is_dir():
        return ["docs/screens does not exist"]
    shots = sorted(
        p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in SCREEN_SUFFIXES
    )
    problems = [
        f"docs/screens/{p.name} is {p.stat().st_size} bytes, over {SCREEN_MAX_BYTES}"
        for p in shots
        if p.stat().st_size >= SCREEN_MAX_BYTES
    ]
    named: list[Path] = []
    for slug in sorted(route_slugs(root) | set(FLOW_SCREENS)):
        hits = [p for p in shots if names(p.stem, slug)]
        if not hits:
            problems.append(f"no screenshot in docs/screens is named for the screen '{slug}'")
        named += hits
    sizes: dict[tuple[int, int], list[str]] = {}
    for p in dict.fromkeys(named):
        if "desktop" in tokens(p.stem):
            continue
        with Image.open(p) as im:
            sizes.setdefault(im.size, []).append(p.name)
    if len(sizes) > 1:
        shown = "; ".join(f"{w}x{h}: {', '.join(v[:3])}" for (w, h), v in sorted(sizes.items()))
        problems.append(f"the screenshots are not in one device frame, sizes differ ({shown})")
    return problems


def check_gif(root: Path) -> list[str]:
    readme = read(root / "README.md")
    gifs = [src for src in images(readme) if src.lower().split("?")[0].endswith(".gif")]
    if not gifs:
        return ["README.md shows no GIF"]
    problems: list[str] = []
    for src in gifs:
        path = local(root, src)
        if path is None:
            problems.append(f"the GIF {src} is not in the repo")
        elif not path.is_file():
            problems.append(f"the GIF {src} does not exist")
        elif path.stat().st_size >= GIF_MAX_BYTES:
            problems.append(f"the GIF {src} is {path.stat().st_size} bytes, over {GIF_MAX_BYTES}")
        else:
            with Image.open(path) as im:
                if getattr(im, "n_frames", 1) < 2:
                    problems.append(f"the GIF {src} has one frame, so it shows no test")
    return problems


def check_lesson_marks(root: Path) -> list[str]:
    readme = read(root / "README.md")
    found = []
    for src in images(readme):
        path = local(root, src)
        if path is not None and "mark" in src.lower() and path.is_file():
            found.append(path)
    if len(set(found)) < 2:
        return [f"README.md shows {len(set(found))} lesson photos with marks, not 2"]
    return []


def mermaid_blocks(text: str) -> list[str]:
    return re.findall(r"^```mermaid\s*\n(.*?)^```", text, re.S | re.M)


LABELLED_EDGE = re.compile(
    r"(?:--+>|==+>|-\.+->|---)\s*\|[^|\n]+\||--\s+[^\s>-][^\n]*?\s+-->|==\s+[^\n=]+?\s+==>"
)


def check_diagrams(root: Path) -> list[str]:
    blocks = mermaid_blocks(read(root / "README.md"))
    problems: list[str] = []
    if len(blocks) < 3:
        problems.append(f"README.md has {len(blocks)} Mermaid diagrams, not 3")
    if not any(
        b.lstrip().startswith("sequenceDiagram") and re.search(r"gate", b, re.I) for b in blocks
    ):
        problems.append("no sequence diagram of the AI gate in README.md")
    if not any(sum(bool(re.search(rf"\b{t}\b", b)) for t in FHIR_TYPES) >= 3 for b in blocks):
        problems.append("no FHIR resource graph (a diagram naming 3 or more FHIR resources)")
    system_map = [
        b
        for b in blocks
        if re.match(r"\s*(flowchart|graph)\b", b)
        and all(re.search(rf"\b{v}\b", b, re.I) for v in FIVE_VERBS)
    ]
    if not system_map:
        problems.append("no system map by the five verbs (Train, Check, Verify, Record, Act)")
    elif not any(LABELLED_EDGE.search(b) for b in system_map):
        problems.append("the system map's edges carry no labels")
    workflows = root / ".github" / "workflows"
    ci = [read(p) for p in sorted(workflows.glob("*.y*ml"))] if workflows.is_dir() else []
    # CI renders the diagrams when a workflow installs the pinned renderer and runs make check,
    # whose diagrams target draws every source again (tools/diagrams/render.mjs --check); or when
    # a workflow sets MERMAID_CLI.
    makefile = read(root / "Makefile")
    check_line = next((ln for ln in makefile.splitlines() if ln.startswith("check:")), "")
    renders = "diagrams" in check_line.split() and "render.mjs --check" in makefile
    installs = any("tools/diagrams" in text and "make check" in text for text in ci)
    if not any("MERMAID_CLI" in text for text in ci) and not (renders and installs):
        problems.append(
            "CI does not render the diagrams: no workflow installs tools/diagrams "
            "and runs make check with its render"
        )
    return problems


ONE_SENTENCE = re.compile(r"[^.!?]*[A-Za-z][^.!?]*[.!?]")
README_ORDER = (
    ("numbers at a glance", r"at a glance"),
    ("the gallery", r"gallery"),
    ("why trust a volunteer and the AI", r"why trust"),
    ("what the AI cannot do", r"what the ai (cannot|can't|can not) do"),
    ("architecture", r"architecture"),
    ("how OneAquaHealth is used", r"how oneaquahealth is used"),
    ("evals", r"\bevals?\b"),
    ("real versus synthetic", r"\breal\b.*\bsynthetic\b"),
    ("quickstart", r"quick ?start"),
    ("for judges", r"for judges"),
    ("known weaknesses", r"known weaknesses"),
    ("how this was built", r"how this was built"),
    ("credits", r"credits"),
    ("repo map", r"repo(sitory)? map"),
    ("licence", r"licen[cs]e"),
)


def plain(line: str) -> str:
    return re.sub(r"[>*_`]", "", line).strip()


def check_readme_order(root: Path) -> list[str]:
    """The judge-first order of UPDATE_27 section 3, block 23, as an ordered walk down the file."""
    lines = read(root / "README.md").splitlines()
    if not lines:
        return ["README.md is missing"]
    problems: list[str] = []
    statement = read(root / "docs" / "track_statement.md").strip()
    filled = [i for i, ln in enumerate(lines) if ln.strip()]
    pos = filled[0] if filled else 0
    if not statement or lines[pos].strip() != statement:
        problems.append("1 track statement: the first line is not docs/track_statement.md")

    # Steps 2 to 6 are the top of the page, above the first section heading.
    top = next((h.line for h in headings(lines) if h.level >= 2), len(lines))

    def find(test: Callable[[str], bool], after: int, limit: int = top) -> int | None:
        return next((i for i in range(after + 1, limit) if test(lines[i])), None)

    def step(label: str, found: int | None) -> None:
        nonlocal pos
        if found is None:
            problems.append(f"{label}: not found after line {pos + 1}")
        else:
            pos = found

    def is_text(line: str) -> bool:
        s = line.strip()
        return bool(s) and not s.startswith(("#", "<!--", "[![", "![", "|", "<")) and bool(plain(s))

    sentence = find(is_text, pos)
    if sentence is not None and not ONE_SENTENCE.fullmatch(plain(lines[sentence])):
        problems.append(f"2 the one sentence: line {sentence + 1} is not one sentence")
    step("2 the one sentence", sentence)
    step("3 badges", find(lambda s: "img.shields.io" in s or "badge.svg" in s, pos))
    badges = pos
    question = find(lambda s: "Which creek is healthier?" in s, badges)
    step("4 the question 'Which creek is healthier?'", question)
    warmups = [i for i in range(badges + 1, top) for src in images(lines[i]) if "warmup" in src]
    if len(warmups) < 2:
        problems.append("4 the two warm-up photos: fewer than two warm-up photos after the badges")
    else:
        pos = max(pos, warmups[1])
    opened = find(lambda s: "<details" in s, pos)
    step("4 the answer in a details block", opened)
    if opened is not None:
        closed = find(lambda s: "</details>" in s, opened - 1, len(lines))
        body = " ".join(lines[opened : (closed or opened) + 1])
        if closed is None or "<summary" not in body:
            problems.append("4 the details block has no <summary> or never closes")
        else:
            pos = closed
    step("5 three links", find(lambda s: len(LINK_MD.findall(s)) >= 3, pos))
    step("6 the GIF", find(lambda s: any(x.lower().endswith(".gif") for x in images(s)), pos))
    pos = max(pos, top - 1)
    for n, (label, pattern) in enumerate(README_ORDER, 7):
        found = section(lines, pattern, pos)
        if found and label == "quickstart" and not any("make judge-check" in b for b in found[1]):
            problems.append(f"{n} quickstart: its section does not say make judge-check")
        step(f"{n} {label}", found[0].line if found else None)
    return problems


def check_social_image(root: Path) -> list[str]:
    found: list[str] = []
    places = [root / "docs", root / ".github", root / "apps" / "web" / "public"]
    candidates = [p for p in root.iterdir() if p.is_file()]
    for place in places:
        if place.is_dir():
            candidates += [
                p
                for p in place.rglob("*")
                if p.is_file() and not WALK_SKIP & set(p.relative_to(root).parts)
            ]
    too_big: list[str] = []
    for p in candidates:
        if p.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        try:
            with Image.open(p) as im:
                size = im.size
        except OSError:
            continue
        if size == SOCIAL_SIZE:
            rel = str(p.relative_to(root))
            (found if p.stat().st_size < SOCIAL_MAX_BYTES else too_big).append(rel)
    if found:
        return []
    if too_big:
        return [f"{', '.join(too_big)} is 1280 by 640 but 1 MB or more, which GitHub refuses"]
    return ["no 1280 by 640 image in the repo for the social preview"]


# ---------------------------------------------------------------------------------------------
# Block 24: the Tideline layer

FILE_RE = re.compile(
    r"(?<![\w/.-])((?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+\.(?:py|ts|tsx|mjs|js|json|jsonl|yaml|yml|md|fsh|toml|csv|sql))\b"
)
TEST_RE = re.compile(
    r"((?:[A-Za-z0-9_.-]+/)+(?:test_[A-Za-z0-9_]+\.py|[A-Za-z0-9_.-]+\.(?:test|spec)\.(?:ts|mjs|js)))"
    r"(?:::([A-Za-z0-9_]+))?"
)


def readme_lines(root: Path) -> list[str]:
    return read(root / "README.md").splitlines()


def check_gate_steps(root: Path) -> list[str]:
    # The first section about the gate that holds numbered steps; an earlier heading that only
    # names the gate, such as a diagram's, does not hide it.
    lines = readme_lines(root)
    found = section(lines, r"\bgate\b")
    if not found:
        return ["README.md has no section about the gate"]
    after = found[0].line
    while not list_items(found[1], numbered_only=True):
        nxt = section(lines, r"\bgate\b", after)
        if nxt is None:
            break
        found, after = nxt, nxt[0].line
    heading, body = found
    steps = list_items(body, numbered_only=True)
    problems: list[str] = []
    if len(steps) < 3:
        problems.append(
            f"the gate section '{heading.title}' has {len(steps)} numbered steps, not 3 or more"
        )
    named: set[str] = set()
    for n, text in enumerate(steps, 1):
        files = FILE_RE.findall(text)
        if not files:
            problems.append(f"gate step {n} names no file")
        for f in files:
            named.add(f)
            if not (root / f).exists():
                problems.append(f"gate step {n} names {f}, which does not exist")
    if steps and "core/gate.py" not in named:
        problems.append("the gate steps never name core/gate.py")
    return problems


def check_properties(root: Path) -> list[str]:
    found = section(readme_lines(root), r"propert(y|ies)")
    if not found:
        return ["README.md has no section of properties"]
    _, body = found
    entries = list_items(body) + [" | ".join(r) for t in tables(body) for r in t[1:]]
    tied = 0
    problems: list[str] = []
    for text in entries:
        refs = TEST_RE.findall(text)
        good = True
        for path, name in refs:
            file = root / path
            if not file.is_file():
                problems.append(f"property names the test {path}, which does not exist")
                good = False
            elif name and name not in read(file):
                problems.append(f"property names {path}::{name}, which is not in that file")
                good = False
        tied += bool(refs) and good
    if tied < 3:
        problems.append(f"{tied} properties are tied to a test that exists, not 3")
    return problems


def check_writeup(root: Path) -> list[str]:
    text = read(root / "WRITEUP.md")
    if not text:
        return ["WRITEUP.md does not exist"]
    lines = text.splitlines()
    problems = []
    if len([h for h in headings(lines) if h.level == 2]) < 3:
        problems.append("WRITEUP.md has fewer than three sections")
    if not any(re.search(r"challenge", h.title, re.I) for h in headings(lines)):
        problems.append("WRITEUP.md has no heading about the engineering challenges")
    links = LINK_MD.findall(read(root / "README.md"))
    if not any(h.split("#")[0].endswith("WRITEUP.md") for h in links):
        problems.append("README.md does not link to WRITEUP.md")
    return problems


def check_security(root: Path) -> list[str]:
    found = section(readme_lines(root), r"security.*privacy|privacy.*security")
    if not found:
        return ["README.md has no security and privacy section"]
    _, body = found
    problems = []
    if len([b for b in body if b.strip()]) < 3:
        problems.append("the security and privacy section is under three lines")
    text = "\n".join(body)
    if "DATA_HANDLING.md" not in text:
        problems.append("the security and privacy section does not point at docs/DATA_HANDLING.md")
    for href in LINK_MD.findall(text):
        path = local(root, href)
        if path is not None and not path.exists():
            problems.append(f"the security and privacy section links {href}, which does not exist")
    return problems


ROUTE = re.compile(r"(/(?:api|health)[^\s|`)]*)")
METHOD = re.compile(r"\b(GET|POST|PUT|PATCH|DELETE)\b")


def code_text(root: Path) -> str:
    parts = []
    for folder, pattern in (("worker/src", "*.ts"), ("apps/api", "*.py")):
        base = root / folder
        if base.is_dir():
            parts += [read(p) for p in base.rglob(pattern) if "node_modules" not in p.parts]
    return "\n".join(parts)


def check_api_table(root: Path) -> list[str]:
    lines = readme_lines(root)
    rows: list[str] = []
    after = -1
    while (found := section(lines, r"\bAPI\b", after)) is not None:
        heading, body = found
        rows = [
            " | ".join(r)
            for t in tables(body)
            for r in t[1:]
            if METHOD.search(" ".join(r)) and ROUTE.search(" ".join(r))
        ]
        if rows:
            break
        after = heading.line
    if not rows:
        return [
            "README.md has no API table (a table of methods and /api routes under an API heading)"
        ]
    problems = []
    if len(rows) < 5:
        problems.append(f"the API table lists {len(rows)} routes, fewer than 5")
    code = code_text(root)
    for row in rows:
        m = ROUTE.search(row)
        assert m is not None
        prefix = re.split(r"[{<:?*]", m.group(1))[0].rstrip("/") or m.group(1)
        if prefix not in code:
            problems.append(
                f"the API table lists {m.group(1)}, which no route in worker/src or apps/api serves"
            )
    return problems


def mcp_tools(root: Path) -> set[str]:
    lines = read(root / "apps" / "mcp" / "server.py").splitlines()
    tools: set[str] = set()
    waiting = False
    for line in lines:
        s = line.strip()
        if s.startswith("@server.tool"):
            waiting = True
        elif waiting and s.startswith("def "):
            tools.add(s[4:].split("(")[0].strip())
            waiting = False
    return tools


def check_mcp_table(root: Path) -> list[str]:
    found = section(readme_lines(root), r"\bMCP\b")
    if not found:
        return ["README.md has no MCP section"]
    listed = {
        word
        for t in tables(found[1])
        for r in t[1:]
        if r
        for word in BACKTICKED.findall(r[0])
        if re.fullmatch(r"[a-z_]+", word)
    }
    tools = mcp_tools(root)
    problems = []
    if not listed:
        problems.append("the MCP section has no table of tools")
    for name in sorted(tools - listed):
        problems.append(f"the MCP table leaves out the tool {name}")
    for name in sorted(listed - tools):
        problems.append(f"the MCP table lists {name}, which apps/mcp/server.py does not define")
    return problems


def check_tech_stack(root: Path) -> list[str]:
    found = section(readme_lines(root), r"tech(nology)? stack")
    if not found:
        return ["README.md has no tech stack section"]
    body = found[1]
    rows = sum(len(t) - 1 for t in tables(body)) + len(list_items(body))
    return [] if rows >= 5 else [f"the tech stack lists {rows} parts, fewer than 5"]


def make_targets(root: Path) -> set[str]:
    return set(re.findall(r"^([A-Za-z0-9_.-]+):", read(root / "Makefile"), re.M))


def check_run_locally(root: Path) -> list[str]:
    found = section(readme_lines(root), r"run(ning)?\b.*\blocally")
    if not found:
        return ["README.md has no running locally section"]
    body = found[1]
    text = "\n".join(body)
    problems = []
    if "offline" not in text.lower():
        problems.append("the running locally section does not say how to run offline")
    if not any(FENCE.match(b) for b in body):
        problems.append("the running locally section has no command block")
    named = set(re.findall(r"\bmake\s+([a-z][a-z0-9-]*)", text))
    if not named:
        problems.append("the running locally section names no make target")
    for target in sorted(named - make_targets(root)):
        problems.append(f"the running locally section runs make {target}, which the Makefile lacks")
    return problems


def check_tests_paragraph(root: Path) -> list[str]:
    found = section(readme_lines(root), r"^tests?\b")
    if not found:
        return ["README.md has no Tests section"]
    markers = len(MARKER.findall("\n".join(found[1])))
    if markers < 2:
        return [f"the Tests section has {markers} counts traced to results/, fewer than 2"]
    return []


CONFIG_PLACES = (
    ".env.example",
    "worker/wrangler.jsonc",
    "apps/web/wrangler.jsonc",
    "apps/api/settings.py",
    "Makefile",
    "docker-compose.yml",
    "apps/web/next.config.ts",
    "apps/web/package.json",
    "apps/web/Dockerfile",
)
CONFIG_GLOBS = (
    ("worker/src", "*.ts"),
    ("apps/web/lib", "*.ts"),
    ("apps/web/scripts", "*.mjs"),
    ("apps/api", "*.py"),
    ("scripts", "*.py"),
    ("scripts", "*.sh"),
    (".github/workflows", "*.yml"),
    ("evals", "*.py"),
    ("core", "*.py"),
    ("apps/web/app", "*.tsx"),
    ("apps/web/components", "*.tsx"),
    ("apps/web/tests", "*.ts"),
    ("worker/test", "*.mjs"),
)


def check_deploy_doc(root: Path) -> list[str]:
    text = read(root / "DEPLOY.md")
    if not text:
        return ["DEPLOY.md does not exist"]
    config = [
        t
        for t in tables(text.splitlines())
        if t and any(re.search(r"setting|variable|name|key", c, re.I) for c in t[0])
    ]
    if not config:
        return [
            "DEPLOY.md has no configuration table (a header with Setting, Variable, Name or Key)"
        ]
    rows = [r for t in config for r in t[1:]]
    problems = []
    if len(rows) < 5:
        problems.append(f"the configuration table has {len(rows)} rows, fewer than 5")
    haystack = "\n".join(read(root / p) for p in CONFIG_PLACES)
    for folder, pattern in CONFIG_GLOBS:
        base = root / folder
        if base.is_dir():
            haystack += "\n".join(
                read(p) for p in base.rglob(pattern) if "node_modules" not in p.parts
            )
    for r in rows:
        spans = BACKTICKED.findall(r[0]) if r else []
        if not spans:
            problems.append(
                f"configuration row '{r[0] if r else ''}' does not name its setting in backticks"
            )
        for name in spans:
            # pydantic settings read an environment name case-insensitively (content_root is
            # CONTENT_ROOT), so the name counts wherever it appears in any case.
            if name.lower() not in haystack.lower():
                problems.append(
                    f"the configuration table names {name}, which no config or code file uses"
                )
    return problems


ADR_NAME = re.compile(r"^(adr-)?\d{3,4}-[a-z0-9-]+\.md$", re.I)


def check_adrs(root: Path) -> list[str]:
    folder = root / "docs" / "adr"
    adrs = (
        sorted(p for p in folder.glob("*.md") if ADR_NAME.match(p.name)) if folder.is_dir() else []
    )
    problems = []
    if not 8 <= len(adrs) <= 10:
        problems.append(f"docs/adr holds {len(adrs)} numbered ADRs, not 8 to 10")
    for p in adrs:
        text = read(p)
        for part in ("Status", "Context", "Decision", "Consequences"):
            if not re.search(rf"^(-\s*)?(#+\s*|\*\*)?{part}\b", text, re.M | re.I):
                problems.append(f"docs/adr/{p.name} has no {part} part")
    return problems


def check_dependabot(root: Path) -> list[str]:
    path = root / ".github" / "dependabot.yml"
    try:
        doc = yaml.safe_load(read(path)) if path.is_file() else None
    except yaml.YAMLError as e:
        return [f".github/dependabot.yml is not YAML: {e}"]
    if not isinstance(doc, dict):
        return [".github/dependabot.yml does not exist"]
    problems = []
    if doc.get("version") != 2:
        problems.append(".github/dependabot.yml is not version 2")
    updates = [u for u in doc.get("updates") or [] if isinstance(u, dict)]
    kinds = {u.get("package-ecosystem") for u in updates}
    for need in ("github-actions", "npm"):
        if need not in kinds:
            problems.append(f"Dependabot does not watch {need}")
    if not kinds & {"pip", "uv"}:
        problems.append("Dependabot does not watch the Python dependencies (pip or uv)")
    npm_dirs: set[str] = set()
    for u in updates:
        if u.get("package-ecosystem") == "npm":
            dirs = u.get("directories") or [u.get("directory", "")]
            npm_dirs |= {str(d).strip("/") for d in dirs}
    for need in ("apps/web", "worker"):
        if "npm" in kinds and need not in npm_dirs:
            problems.append(f"Dependabot's npm updates leave out {need}")
    return problems


def check_precommit(root: Path) -> list[str]:
    path = root / ".pre-commit-config.yaml"
    try:
        doc = yaml.safe_load(read(path)) if path.is_file() else None
    except yaml.YAMLError as e:
        return [f".pre-commit-config.yaml is not YAML: {e}"]
    if not isinstance(doc, dict):
        return [".pre-commit-config.yaml does not exist"]
    hooks = [h for r in doc.get("repos") or [] for h in (r or {}).get("hooks") or []]
    words = " ".join(
        f"{h.get('id', '')} {h.get('entry', '')}" for h in hooks if isinstance(h, dict)
    )
    problems = []
    if not hooks:
        problems.append(".pre-commit-config.yaml has no hooks")
    if "ruff" not in words:
        problems.append("pre-commit does not run ruff")
    if "check_dashes" not in words:
        problems.append("pre-commit does not run scripts/check_dashes.py")
    return problems


# ---------------------------------------------------------------------------------------------
# Hardening


def numbered(folder: Path, prefix: str) -> list[tuple[int, Path]]:
    pattern = re.compile(rf"^{prefix}_(\d+)[A-Za-z0-9_-]*\.md$")
    found = []
    for p in folder.glob(f"{prefix}_*.md") if folder.is_dir() else ():
        m = pattern.match(p.name)
        if m:
            found.append((int(m.group(1)), p))
    return sorted(found)


REVIEWED_COMMIT = re.compile(r"\bcommit:?\s+`?([0-9a-f]{7,40})\b", re.I)
REVIEWS = ("docs", "internal", "reviews")


def check_review(root: Path) -> list[str]:
    reviews = numbered(root.joinpath(*REVIEWS), "REVIEW")
    if len(reviews) < 2:
        return [f"{len(reviews)} adversarial reviews in the reviews folder, not 2"]
    n, path = reviews[-1]
    m = REVIEWED_COMMIT.search(read(path))
    problem = commit_problem(root, m.group(1) if m else None, path.name)
    return [f"{problem} (the second review reads the finished repo)"] if problem else []


def check_critics(root: Path) -> list[str]:
    rounds = numbered(root.joinpath(*REVIEWS), "CRITIC")
    if len(rounds) < 2:
        return [f"{len(rounds)} critic rounds in the reviews folder, not 2 or more"]
    problems = []
    for _, path in rounds[-2:]:
        text = read(path)
        sev = re.search(r"^Highest severity:\s*([A-Za-z][A-Za-z -]*?)\s*$", text, re.M | re.I)
        if not sev:
            problems.append(
                f"{path.name} has no line 'Highest severity: <none or cosmetic or ...>'"
            )
        elif sev.group(1).strip().lower() not in LOW_SEVERITY:
            problems.append(f"{path.name} reports '{sev.group(1).strip()}', above cosmetic")
        m = re.search(r"^Commit:\s*`?([0-9a-f]{7,40})\b", text, re.M)
        problem = commit_problem(root, m.group(1) if m else None, path.name)
        if problem:
            problems.append(problem)
    return problems


def check_judge_sim(root: Path) -> list[str]:
    sims = numbered(root.joinpath(*REVIEWS), "JUDGE_SIM")
    if len(sims) < 2 or sims[-1][0] < 1:
        return [
            "no rerun of the six-judge simulation (a JUDGE_SIM_01 or later beside JUDGE_SIM_00)"
        ]
    _, path = sims[-1]
    text = read(path)
    judges = [
        r
        for t in tables(text.splitlines())
        for r in t[1:]
        if r
        and "mean" not in r[0].lower()
        and sum(bool(re.fullmatch(r"\*{0,2}\d+(\.\d+)?\*{0,2}", c)) for c in r) >= 5
    ]
    problems = []
    if len(judges) != 6:
        problems.append(f"{path.name} scores {len(judges)} judges, not 6")
    m = REVIEWED_COMMIT.search(text)
    problem = commit_problem(root, m.group(1) if m else None, path.name)
    if problem:
        problems.append(problem)
    return problems


def check_axe(root: Path) -> list[str]:
    doc, problems = results_file(root, "axe.json")
    if doc is None:
        return problems
    screens = [s for s in doc.get("screens") or [] if isinstance(s, dict)]
    if not screens:
        problems.append("axe.json checked no screen")
    for s in screens:
        where = f"{s.get('path')} ({s.get('viewport')})"
        if s.get("status") != 200 or s.get("error"):
            problems.append(
                f"axe could not check {where}: status {s.get('status')} {s.get('error') or ''}"
            )
        for v in s.get("violations") or []:
            problems.append(f"axe: {v.get('id') if isinstance(v, dict) else v} on {where}")
    if not any(s.get("path") == "/accessibility" for s in screens):
        problems.append("axe.json does not check the /accessibility page")
    if not (root / "apps" / "web" / "app" / "accessibility" / "page.tsx").is_file():
        problems.append("the web app has no /accessibility page")
    return problems


LIGHTHOUSE_MIN = {"performance": 90, "accessibility": 95}


def check_lighthouse(root: Path) -> list[str]:
    doc, problems = results_file(root, "lighthouse.json")
    if doc is None:
        return problems
    pages = [p for p in doc.get("pages") or [] if isinstance(p, dict)]
    if not pages:
        problems.append("lighthouse.json measured no page")
    for p in pages:
        median = p.get("median")
        if p.get("status") != 200 or not isinstance(median, dict):
            problems.append(f"Lighthouse did not measure {p.get('url')}: status {p.get('status')}")
            continue
        for score, least in LIGHTHOUSE_MIN.items():
            got = (median.get("scores") or {}).get(score)
            if not isinstance(got, (int, float)) or got < least:
                problems.append(f"{p.get('url')}: {score} {got}, under {least}")
    return problems


def check_load(root: Path) -> list[str]:
    rel = "results/harden/load_live.json"
    doc = load_json(root / rel)
    if not isinstance(doc, dict):
        return [f"{rel} is missing or is not JSON"]
    problems = []
    finished = parse_utc(doc.get("finished_utc"))
    if finished is None or finished < base_time(root):
        problems.append(
            f"{rel} finished at {doc.get('finished_utc')}, before {BASE_COMMIT}; run it again"
        )
    started, done = doc.get("sessions_started"), doc.get("sessions_done")
    if not isinstance(started, int) or started <= 0 or done != started:
        problems.append(f"the load test finished {done} of {started} sessions")
    if doc.get("session_error_count") != 0:
        problems.append(f"the load test had {doc.get('session_error_count')} session errors")
    for e in doc.get("endpoints") or []:
        if e.get("ok") != e.get("requests"):
            problems.append(
                f"{e.get('endpoint')}: {e.get('ok')} of {e.get('requests')} answered well"
            )
    return problems


def check_flaky(root: Path) -> list[str]:
    doc, problems = results_file(root, "flaky.json")
    if doc is None:
        return problems
    runs = [r for r in doc.get("runs") or [] if isinstance(r, dict)]
    if len(runs) < 3:
        problems.append(f"flaky.json has {len(runs)} runs, not 3")
    if doc.get("flaky"):
        problems.append(f"flaky tests: {doc.get('flaky')}")
    for r in runs:
        for name, suite in (r.get("suites") or {}).items():
            if not isinstance(suite, dict) or suite.get("code") != 0:
                code = suite.get("code") if isinstance(suite, dict) else suite
                problems.append(
                    f"run {r.get('run')}: {name} exited {code}, so it was not shown steady"
                )
    return problems


NEVER_RUN = ("not on the safe list: contains", "a template with a placeholder")


def check_readme_commands(root: Path) -> list[str]:
    from scripts import harden_commands

    doc, problems = results_file(root, "commands.json")
    if doc is None:
        return problems
    ran = {c.get("command"): c for c in doc.get("commands") or [] if isinstance(c, dict)}
    wanted = [c["command"] for c in harden_commands.extract(root) if c["doc"] == "README.md"]
    if not wanted:
        problems.append("README.md prints no command, so nothing was executed")
    for cmd in wanted:
        if harden_commands.policy(cmd).startswith(NEVER_RUN):
            continue
        got = ran.get(cmd)
        if got is None:
            problems.append(f"never executed: {cmd}")
        elif not got.get("ran") or got.get("result") != "pass":
            problems.append(f"{got.get('result')}: {cmd}")
    return problems


def check_links(root: Path) -> list[str]:
    doc, problems = results_file(root, "links.json")
    if doc is None:
        return problems
    rows = [r for r in doc.get("rows") or [] if isinstance(r, dict)]
    if not rows:
        problems.append("links.json checked no link")
    dead = [r for r in rows if r.get("status") == "dead"]
    for r in dead[:10]:
        problems.append(f"dead link {r.get('target')} in {r.get('file')}:{r.get('line')}")
    if len(dead) > 10:
        problems.append(f"and {len(dead) - 10} more dead links")
    return problems


# ---------------------------------------------------------------------------------------------
# The submission pack


def run_submit_check(root: Path) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, "scripts/submit_check.py"],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=600,
    )
    return proc.returncode, proc.stdout + proc.stderr


def check_submit_pack(
    root: Path, run: Callable[[Path], tuple[int, str]] = run_submit_check
) -> list[str]:
    from scripts.go_public import submit_failures

    code, out = run(root)
    failed = submit_failures(out)
    if failed is None:
        return [f"make submit-check printed no summary line it could read (exit {code})"]
    others = failed - SUBMIT_ALLOWED
    return [f"make submit-check also fails on {', '.join(sorted(others))}"] if others else []


STEP = re.compile(r"^(\d+)\.\s")
WHEN = re.compile(
    r"\b(Sep|Sept|September|Oct|October)\.? \d{1,2}\b|\b(Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*\b"
)
NOT_HUMAN = re.compile(r"\b(a|the|any|another) session\b|\bsubagent\b|\bClaude\b", re.I)


def human_count(root: Path) -> int:
    try:
        items = done_check.parse(read(root.joinpath("docs", "internal", "DONE.md")))
    except done_check.ChecklistError:
        return 0
    return sum(1 for i in items if i.kind == "HUMAN")


def check_alex_todo(root: Path) -> list[str]:
    text = read(root / "docs" / "ALEX_TODO.md")
    if not text:
        return ["docs/ALEX_TODO.md does not exist"]
    steps: list[list[str]] = []
    current: list[str] | None = None
    for line in text.splitlines():
        if STEP.match(line):
            current = [line]
            steps.append(current)
        elif current is not None and (line.startswith((" ", "\t")) or not line.strip()):
            current.append(line)
        else:
            current = None  # a paragraph ends the list
    problems = []
    if not steps:
        problems.append("docs/ALEX_TODO.md has no numbered steps")
    for s in steps:
        n = STEP.match(s[0])
        label = n.group(1) if n else "?"
        if not WHEN.search(s[0]):
            problems.append(f"step {label} gives no date or day")
        hit = NOT_HUMAN.search(" ".join(s))
        if hit:
            problems.append(f"step {label} mentions '{hit.group(0)}': a step for a person only")
    humans = human_count(root)
    if len(steps) > humans:
        problems.append(f"{len(steps)} steps, more than the {humans} HUMAN items in the checklist")
    return problems


# ---------------------------------------------------------------------------------------------
# Dated items


def check_data_lock(root: Path) -> list[str]:
    for line in read(root / "audit" / "log.jsonl").splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        when = parse_utc(entry.get("ts_utc"))
        if entry.get("kind") == "data_lock" and when is not None and when >= DATA_LOCK_UTC:
            return []
    return ["audit/log.jsonl has no data_lock entry at or after the lock"]


def check_analysis_once(root: Path) -> list[str]:
    real = []
    for p in sorted((root / "results").glob("usability_*.json")):
        if not re.fullmatch(r"usability_\d{8}\.json", p.name):
            continue
        doc = load_json(p)
        if isinstance(doc, dict) and doc.get("synthetic") is False:
            real.append((p, doc))
    if len(real) != 1:
        return [f"{len(real)} real analysis results in results/, not exactly 1"]
    path, doc = real[0]
    problems = []
    when = parse_utc(doc.get("generated_at_utc"))
    if when is None or when < DATA_LOCK_UTC:
        problems.append(f"{path.name} was made at {doc.get('generated_at_utc')}, before the lock")
    status = (doc.get("primary") or {}).get("status")
    if status not in ("descriptive", "confirmatory"):
        problems.append(f"{path.name} does not say whether it is a description or a test")
    return problems


def check_sandbox_repush(root: Path) -> list[str]:
    for line in read(root / "fhir" / "sandbox_ledger.jsonl").splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        when = parse_utc(entry.get("ts_utc"))
        if (
            when is not None
            and when >= DATA_LOCK_UTC
            and entry.get("action") in ("create", "update")
        ):
            return []
    return ["fhir/sandbox_ledger.jsonl has no push at or after the lock"]


# ---------------------------------------------------------------------------------------------
# Human items


def probe_seconds(path: Path) -> float:
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    try:
        return float(proc.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return 0.0


def check_voice(root: Path, probe: Callable[[Path], float] = probe_seconds) -> list[str]:
    media = Path(os.environ.get("SECOND_LOOK_MEDIA", str(Path.home() / "second-look-media")))
    folder = media / "voice"
    audio = (
        sorted(p for p in folder.glob("*") if p.suffix.lower() in AUDIO_SUFFIXES)
        if folder.is_dir()
        else []
    )
    if not audio:
        return [f"no recording in {folder}"]
    longest = max(probe(p) for p in audio)
    if longest < VOICE_MIN_SECONDS:
        return [
            f"the longest recording in {folder} runs {longest:.0f} s, under {VOICE_MIN_SECONDS:.0f}"
        ]
    return []


def fetch(url: str) -> tuple[int, str]:
    try:
        r = httpx.get(
            url, timeout=20, follow_redirects=True, headers={"User-Agent": "second-look-done-check"}
        )
    except httpx.HTTPError:
        return 0, ""
    return r.status_code, r.text


def check_video_link(root: Path, get: Fetch = fetch) -> list[str]:
    from scripts.submit_check import video_links

    problems = []
    links: list[str] = []
    for rel in ("README.md", "docs/devpost.md"):
        found = video_links(read(root / rel))
        if not found:
            problems.append(f"{rel} has no line with the word video and a link")
        links += found
    if links:
        status, _ = get(links[0])
        if status != 200:
            problems.append(f"the video link {links[0]} answered {status or 'nothing'}, not 200")
    return problems


def devpost_link(root: Path) -> str | None:
    m = DEVPOST_RE.search(read(root / "docs" / "devpost.md"))
    return m.group(0) if m else None


def check_devpost_page(root: Path, get: Fetch = fetch) -> list[str]:
    url = devpost_link(root)
    if url is None:
        return ["docs/devpost.md names no devpost.com/software page"]
    status, _ = get(url)
    return [] if status == 200 else [f"{url} answered {status or 'nothing'}, not 200"]


def check_devpost_submitted(root: Path, get: Fetch = fetch) -> list[str]:
    url = devpost_link(root)
    if url is None:
        return ["docs/devpost.md names no devpost.com/software page"]
    status, text = get(url)
    if status != 200:
        return [f"{url} answered {status or 'nothing'}, not 200"]
    return (
        [] if re.search(r"submitted to", text, re.I) else [f"{url} does not say it was submitted"]
    )


CHECKS: dict[str, Check] = {
    "screens": check_screens,
    "gif": check_gif,
    "lesson-marks": check_lesson_marks,
    "diagrams": check_diagrams,
    "readme-order": check_readme_order,
    "social-image": check_social_image,
    "gate-steps": check_gate_steps,
    "properties": check_properties,
    "writeup": check_writeup,
    "security": check_security,
    "api-table": check_api_table,
    "mcp-table": check_mcp_table,
    "tech-stack": check_tech_stack,
    "run-locally": check_run_locally,
    "tests-paragraph": check_tests_paragraph,
    "deploy-doc": check_deploy_doc,
    "adrs": check_adrs,
    "dependabot": check_dependabot,
    "precommit": check_precommit,
    "review": check_review,
    "critics": check_critics,
    "judge-sim": check_judge_sim,
    "axe": check_axe,
    "lighthouse": check_lighthouse,
    "load": check_load,
    "flaky": check_flaky,
    "readme-commands": check_readme_commands,
    "links": check_links,
    "submit-pack": check_submit_pack,
    "alex-todo": check_alex_todo,
    "data-lock": check_data_lock,
    "analysis-once": check_analysis_once,
    "sandbox-repush": check_sandbox_repush,
    "voice": check_voice,
    "video-link": check_video_link,
    "devpost-page": check_devpost_page,
    "devpost-submitted": check_devpost_submitted,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("check", nargs="?", choices=sorted(CHECKS), help="the check to run")
    parser.add_argument("--list", action="store_true", help="print every check's name")
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.list or not args.check:
        print("\n".join(sorted(CHECKS)))
        return 0 if args.list else 2
    problems = CHECKS[args.check](args.root.resolve())
    for p in problems:
        print(f"  {p}")
    # The last line is the one done-check shows on a RED line, so it names the first gap.
    if problems:
        print(f"done-item {args.check}: {len(problems)} missing, first: {problems[0]}")
    else:
        print(f"done-item {args.check}: ok")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
