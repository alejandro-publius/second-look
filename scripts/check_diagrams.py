"""Every Mermaid block in the docs parses (Update 10 tier 3 item 6).

A broken diagram in a README is invisible on GitHub: the block renders as an error box, or as
nothing, and nobody notices until a judge opens the page. This walks every fenced ```mermaid
block in the tracked Markdown and checks it with the Mermaid CLI when that is installed, and
with a small structural parser when it is not, so `make check` is useful offline too.

What the offline parser checks, which is what actually breaks in practice:

- the block names a diagram type we use (flowchart, graph, sequenceDiagram, erDiagram)
- brackets, braces and parentheses balance on every line
- `subgraph` and `end` pair up, and in a sequence diagram `alt`, `opt`, `loop` and the rest
- an arrow has something on both sides of it
- a node label with a bracket or a quote inside it is quoted

The three diagrams of UPDATE_27 block 23 live as sources in docs/diagrams/*.mmd, each drawn as an
SVG next to it by tools/diagrams/render.mjs. This script checks them offline too, before the
render check in `make diagrams` runs a browser:

- each source passes the structural check above, and names itself with accTitle and accDescr,
  which become the SVG's title and description for a screen reader
- in a flowchart source, every edge carries a label that says what flows along it, and every
  line of a label in the SVG is a line the source wrote, so Mermaid never wrapped one on its own
- each source has its SVG, each SVG has its source, and the stamp on the SVG's first line carries
  the sha256 of the source as it is now, so a source edited without a new render fails here, and
  the sha256 of the drawing under it, so an SVG edited by hand fails too
- a Markdown block that names the same accTitle as a source is a copy of it, and must be the
  source word for word, so a copy in the README or docs/ARCHITECTURE.md cannot drift

Run: uv run python scripts/check_diagrams.py
     MERMAID_CLI=1 uv run python scripts/check_diagrams.py   also run npx @mermaid-js/mermaid-cli
"""

from __future__ import annotations

import hashlib
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIAGRAM_DIR = Path("docs") / "diagrams"
SEARCH = ("README.md", "docs")
SKIP_DIRS = {"node_modules", ".next", "out", "ig-src"}
FENCE = re.compile(r"^```mermaid\s*$")
CLOSE = re.compile(r"^```\s*$")
TYPES = ("flowchart", "graph", "sequenceDiagram", "erDiagram", "classDiagram", "stateDiagram")
# What an end closes in a sequence diagram. In a flowchart only a subgraph opens a block.
SEQUENCE_BLOCKS = ("alt", "opt", "loop", "par", "critical", "break", "rect", "box")
ARROWS = ("-->", "---", "-.->", "==>", "->>", "-->>", "->", "--)", "--x")
# A flowchart edge with its label, in the two spellings Mermaid knows:
#   A -- "what flows" --> B    (also -. "x" .-> B, == "x" ==> B, A <-- "x" --> B)
#   A -->|what flows| B
#   An edge may also end in a circle or a cross (A --o B, A x--x B), so those ends count too.
LABELLED_EDGE = re.compile(
    r'^\w+\s*[<ox]?(?:--|-\.|==)\s*"[^"]*\S[^"]*"\s*(?:-->|\.->|==>|---|[-.=][-=][ox])\s*\w+$'
    r"|^\w+\s*[<ox]?(?:-->|-\.->|==>|---|[-.=][-=][ox])\s*\|[^|]*\S[^|]*\|\s*\w+$"
)
EDGE_TOKENS = ("-->", ".->", "==>", "---", "~~~", "-.-", "--o", "--x", "==o", "==x", ".-o", ".-x")
NOT_EDGES = ("subgraph ", "accTitle", "accDescr", "classDef ", "class ", "style ", "linkStyle ")
STAMP = re.compile(
    r"^<!-- Drawn by make diagrams from docs/diagrams/(\S+)\.mmd \(sha256 ([0-9a-f]{64})\)"
)
# The same first line also carries the sha256 of the drawing below it, so a hand edit shows.
DRAWING = re.compile(r"the drawing below has sha256 ([0-9a-f]{64})\. ")
ACC_TITLE = re.compile(r"^\s*accTitle:\s*(.+?)\s*$", re.M)
# One line of a label as Mermaid draws it in a flowchart SVG: a row tspan holding one tspan per
# word. Mermaid breaks an edge label on its own once a line is wider than 200 pixels, and where it
# breaks depends on the fonts of the machine, so every row must be a line the source wrote.
SVG_ROW = re.compile(r'<tspan class="text-outer-tspan row"[^>]*>(.*?)</tspan></tspan>')
SVG_WORD = re.compile(r">([^<]*)")
SOURCE_LABEL = re.compile(r'"([^"]*)"|\|([^|]*)\|')


class DiagramError(Exception):
    pass


def markdown_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for name in SEARCH:
        target = root / name
        if target.is_file():
            files.append(target)
            continue
        if not target.is_dir():
            continue
        for path in sorted(target.rglob("*.md")):
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            files.append(path)
    return files


def blocks_in(path: Path) -> list[tuple[int, str]]:
    """Every mermaid block in the file, as (line number of the fence, source)."""
    out: list[tuple[int, str]] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    index = 0
    while index < len(lines):
        if FENCE.match(lines[index]):
            start = index + 1
            body: list[str] = []
            index += 1
            while index < len(lines) and not CLOSE.match(lines[index]):
                body.append(lines[index])
                index += 1
            out.append((start, "\n".join(body)))
        index += 1
    return out


def _strip_labels(line: str) -> str:
    """Take out quoted text so a bracket inside a label does not read as an unbalanced one."""
    return re.sub(r'"[^"]*"', '""', line)


def check_source(source: str) -> list[str]:
    problems: list[str] = []
    lines = [ln for ln in source.splitlines() if ln.strip() and not ln.strip().startswith("%%")]
    if not lines:
        return ["the block is empty"]
    head = lines[0].strip()
    if not head.startswith(TYPES):
        problems.append(f"line 1 does not name a diagram type we use: {head!r}")
    openers = SEQUENCE_BLOCKS if head.startswith("sequenceDiagram") else ("subgraph",)
    depth = 0
    for number, raw in enumerate(lines, start=1):
        line = _strip_labels(raw)
        stripped = line.strip()
        for open_char, close_char in (("[", "]"), ("{", "}"), ("(", ")")):
            if line.count(open_char) != line.count(close_char):
                problems.append(
                    f"line {number}: {open_char}{close_char} do not balance: {raw.strip()!r}"
                )
        if stripped.split(" ", 1)[0] in openers:
            depth += 1
        elif stripped == "end":
            depth -= 1
            if depth < 0:
                problems.append(f"line {number}: an end with no {' or '.join(openers)} to close")
                depth = 0
        for arrow in ARROWS:
            if arrow not in stripped:
                continue
            left, _, right = stripped.partition(arrow)
            if not left.strip() or not right.strip():
                problems.append(
                    f"line {number}: an arrow with nothing on one side: {raw.strip()!r}"
                )
            break
    if depth != 0:
        problems.append(f"{depth} {' or '.join(openers)} block(s) never closed with end")
    return problems


def unlabelled_edges(source: str) -> list[str]:
    """Every edge in a flowchart that does not say what flows along it, as "line N: ..."."""
    lines = source.splitlines()
    head = next((ln.strip() for ln in lines if ln.strip() and not ln.strip().startswith("%%")), "")
    if not head.startswith(("flowchart", "graph")):
        return []
    problems: list[str] = []
    for number, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line or line == "end" or line.startswith("%%") or line.startswith(NOT_EDGES):
            continue
        if not any(token in _strip_labels(line) for token in EDGE_TOKENS):
            continue
        if not LABELLED_EDGE.match(line):
            problems.append(
                f"line {number}: an edge with no label, or more than one edge: {line!r}"
            )
    return problems


def wrapped_rows(source: str, svg: str) -> list[str]:
    """Label lines in a flowchart SVG that the source did not write: Mermaid wrapped them itself.

    A wrap moves with the fonts of the machine that draws it, so a label that wraps here may not
    wrap on the CI runner, and the drawing then differs in content. Break long labels with <br/>.
    """
    head = next((ln.strip() for ln in source.splitlines() if ln.strip()), "")
    if not head.startswith(("flowchart", "graph")):
        return []
    lines = set()
    for quoted, piped in SOURCE_LABEL.findall(source):
        for part in re.split(r"<br\s*/?>", quoted or piped):
            lines.add(" ".join(part.split()))
    rows = [html.unescape("".join(SVG_WORD.findall(row))).strip() for row in SVG_ROW.findall(svg)]
    if not rows:
        return ["no label rows found in the SVG, so the wrap check cannot read it"]
    return [f"a label wrapped on its own at {row!r}" for row in rows if row and row not in lines]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def diagram_sources(root: Path) -> list[Path]:
    folder = root / DIAGRAM_DIR
    return sorted(folder.glob("*.mmd")) if folder.is_dir() else []


def source_problems(root: Path) -> list[str]:
    """The .mmd sources in docs/diagrams and the SVGs drawn from them, checked without a browser."""
    folder = root / DIAGRAM_DIR
    sources = diagram_sources(root)
    if not sources:
        return [f"{DIAGRAM_DIR}: no .mmd sources"]
    problems: list[str] = []
    names = {p.stem for p in sources}
    for svg in sorted(folder.glob("*.svg")):
        if svg.stem not in names:
            problems.append(f"{DIAGRAM_DIR / svg.name}: an SVG with no .mmd source next to it")
    titles: dict[str, str] = {}
    for src in sources:
        where = DIAGRAM_DIR / src.name
        raw = src.read_bytes()
        text = raw.decode("utf-8")
        problems += [f"{where}: {p}" for p in check_source(text)]
        title = ACC_TITLE.search(text)
        if title is None:
            problems.append(f"{where}: no accTitle, which names the SVG for a screen reader")
        elif title.group(1) in titles:
            problems.append(f"{where}: the same accTitle as {titles[title.group(1)]}")
        else:
            titles[title.group(1)] = src.name
        if not re.search(r"^\s*accDescr:\s*\S", text, re.M):
            problems.append(f"{where}: no accDescr, which says in words what the diagram shows")
        problems += [f"{where}: {p}" for p in unlabelled_edges(text)]
        svg = src.with_suffix(".svg")
        if not svg.exists():
            problems.append(f"{where}: no SVG next to it; run make diagrams-render")
            continue
        first, _, body = svg.read_bytes().partition(b"\n")
        stamp = STAMP.match(first.decode("utf-8", errors="replace"))
        drawing = DRAWING.search(first.decode("utf-8", errors="replace"))
        if stamp is None or stamp.group(1) != src.stem:
            problems.append(
                f"{DIAGRAM_DIR / svg.name}: no stamp naming {src.name} on its first line"
            )
        elif stamp.group(2) != _sha256(raw):
            problems.append(
                f"{DIAGRAM_DIR / svg.name}: drawn from another version of {src.name}; "
                "run make diagrams-render"
            )
        elif drawing is None or drawing.group(1) != _sha256(body):
            problems.append(
                f"{DIAGRAM_DIR / svg.name}: edited by hand after it was drawn; "
                "run make diagrams-render"
            )
        else:
            problems += [
                f"{DIAGRAM_DIR / svg.name}: {p}; break the line with <br/> in {src.name}"
                for p in wrapped_rows(text, body.decode("utf-8"))
            ]
    return problems


def copy_problems(root: Path, blocks: list[tuple[str, str]]) -> list[str]:
    """A Markdown block with a source's accTitle is a copy of that source and must match it."""
    by_title: dict[str, tuple[str, str]] = {}
    for src in diagram_sources(root):
        text = src.read_text(encoding="utf-8")
        title = ACC_TITLE.search(text)
        if title is not None:
            by_title.setdefault(title.group(1), (src.name, text))
    problems: list[str] = []
    for where, source in blocks:
        title = ACC_TITLE.search(source)
        if title is None or title.group(1) not in by_title:
            continue
        name, text = by_title[title.group(1)]
        if source.rstrip("\n") != text.rstrip("\n"):
            problems.append(
                f"{where}: a copy of {DIAGRAM_DIR / name} that differs from it; "
                "paste the source again"
            )
    return problems


def run_cli(source: str) -> str | None:
    """Render with the Mermaid CLI if it is there. Returns an error message, or None."""
    if shutil.which("npx") is None:
        return None
    with tempfile.TemporaryDirectory(prefix="second-look-mermaid-") as tmp:
        work = Path(tmp)
        src = work / "diagram.mmd"
        src.write_text(source + "\n", encoding="utf-8")
        proc = subprocess.run(
            [
                "npx",
                "--yes",
                "@mermaid-js/mermaid-cli",
                "-i",
                str(src),
                "-o",
                str(work / "out.svg"),
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return (
                (proc.stderr or proc.stdout).strip().splitlines()[-1]
                if (proc.stderr or proc.stdout)
                else "mermaid-cli failed"
            )
    return None


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    use_cli = os.environ.get("MERMAID_CLI") == "1"
    problems: list[str] = []
    blocks: list[tuple[str, str]] = []
    for path in markdown_files(root):
        for line_no, source in blocks_in(path):
            where = f"{path.relative_to(root)}:{line_no}"
            blocks.append((where, source))
            for problem in check_source(source):
                problems.append(f"{where}: {problem}")
            if use_cli:
                error = run_cli(source)
                if error:
                    problems.append(f"{where}: mermaid-cli: {error}")
    problems += source_problems(root)
    problems += copy_problems(root, blocks)
    count = len(blocks)
    sources = len(diagram_sources(root))
    if problems:
        print("\n".join(problems))
        print(f"diagrams: {len(problems)} problem(s) in {count} block(s) and {sources} source(s)")
        return 1
    how = "mermaid-cli and the structural check" if use_cli else "the structural check"
    print(
        f"diagrams: {count} Mermaid block(s) parse, by {how}; {sources} source(s) in "
        f"{DIAGRAM_DIR} have labelled edges and an SVG drawn from them as they are now"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
