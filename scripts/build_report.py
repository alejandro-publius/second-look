"""Build docs/REPORT.pdf from the README, the docs it names and results/ (UPDATE_29 section 5).

Run: uv run python scripts/build_report.py            make report-pdf: the PDF and its stamp
     uv run python scripts/build_report.py --check    fail when the PDF is older than its sources

How it is built. `docs/report/source.md` holds the report's own words. A line that is only
`{{section:FILE#Heading}}` becomes the text under that heading in FILE, up to the next heading of
any level. Every number a section shows through a `<!--v:...-->` marker is compared with
`results/` first, and the build refuses a stale one, so the PDF never carries a number the
README would fail on. `{{claim:...}}` tokens are filled from `results/`. Links to files in this
repository become links to the repository on GitHub. Pandoc, at the version pinned below, turns
the Markdown into HTML with no smart quotes or dashes; `docs/report/template.html` and
`docs/report/report.css` wrap it, with the Atkinson fonts the web app already installs; and
`apps/web/scripts/print-report.mjs` prints it in the Chromium that Playwright installs for
apps/web. Nothing reaches the network.

The stamp is `results/report_pdf.json`: the sha256 of the sources as assembled (the Markdown
after every section and number is put in, the template, the stylesheet and the print script),
the PDF's sha256 and page count, and the tool versions. `scripts/tests/test_report_pdf.py`
assembles the sources again and compares, so a README section or a result that changes after the
PDF was built turns make check red until `make report-pdf` runs again.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from scripts.render_readme import display, resolve

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = Path("docs") / "report"
SOURCE = REPORT_DIR / "source.md"
TEMPLATE = REPORT_DIR / "template.html"
STYLESHEET = REPORT_DIR / "report.css"
PRINTER = Path("apps") / "web" / "scripts" / "print-report.mjs"
PDF = Path("docs") / "REPORT.pdf"
STAMP = Path("results") / "report_pdf.json"
PANDOC_VERSION = "3.9.0.2"
PLAYWRIGHT_VERSION = "1.63.0"
REPO_URL = "https://github.com/alejandro-publius/second-look/blob/main/"
MIN_PAGES, MAX_PAGES = 4, 10
FONT_DIRS = {
    "next": Path("apps/web/node_modules/@fontsource-variable/atkinson-hyperlegible-next"),
    "mono": Path("apps/web/node_modules/@fontsource/atkinson-hyperlegible-mono"),
}

SECTION_RE = re.compile(r"^\{\{section:([\w./-]+)#([^}]+)\}\}$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
RENDERED_RE = re.compile(r"<!--v:([\w./-]+)#([\w/. -]+)-->(.*?)<!--/v-->", re.S)
CLAIM_RE = re.compile(r"<!--\s*claim:\s*([\w./-]+)#([\w/.-]+)\s*(?:=\s*([^\s]+))?\s*-->")
TOKEN_RE = re.compile(r"\{\{claim:([\w./-]+)#([\w/. -]+)\}\}")
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
LOCAL_LINK_RE = re.compile(r"\[([^\]]+)\]\((?!https?://|#|mailto:)([^)\s]+)\)")
DASHES = (chr(0x2013), chr(0x2014))


class ReportError(Exception):
    """The report cannot be built as its sources stand. The message says why in plain words."""


@dataclass
class Assembled:
    markdown: str
    inputs: set[str] = field(default_factory=set)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def section_body(text: str, title: str, where: str = "the file") -> str:
    """The lines under the one heading called `title`, up to the next heading of any level."""
    lines = text.splitlines()
    starts: list[int] = []
    fenced = False
    heads: list[int] = []
    for n, line in enumerate(lines):
        if FENCE_RE.match(line):
            fenced = not fenced
            continue
        m = None if fenced else HEADING_RE.match(line)
        if m:
            heads.append(n)
            if m.group(2) == title:
                starts.append(n)
    if len(starts) != 1:
        found = "no heading" if not starts else f"{len(starts)} headings"
        raise ReportError(f"{where} has {found} called {title!r}")
    start = starts[0]
    end = next((h for h in heads if h > start), len(lines))
    return "\n".join(lines[start + 1 : end]).strip("\n")


def value_of(root: Path, rel: str, pointer: str, inputs: set[str]) -> object:
    inputs.add(rel)
    try:
        return resolve(f"{rel}#{pointer}", root)
    except (FileNotFoundError, KeyError, IndexError, ValueError, json.JSONDecodeError) as exc:
        raise ReportError(f"{rel}#{pointer} cannot be read ({type(exc).__name__})") from exc


def checked_numbers(text: str, root: Path, where: str, inputs: set[str]) -> str:
    """Each rendered number as plain text, after comparing it with results/. Stale ones refuse."""

    def rendered(m: re.Match[str]) -> str:
        rel, pointer, shown = m.group(1), m.group(2), m.group(3)
        now = display(value_of(root, rel, pointer, inputs))
        if now != shown:
            raise ReportError(
                f"{where} shows {shown} for {rel}#{pointer}, but results/ says {now}; "
                "run make render-readme first"
            )
        return shown

    def marker(m: re.Match[str]) -> str:
        rel, pointer, expected = m.group(1), m.group(2), m.group(3)
        now = value_of(root, rel, pointer, inputs)
        if expected is not None and str(now) != expected:
            raise ReportError(f"{where} has a claim marker for {rel}#{pointer} that drifted")
        return ""

    return CLAIM_RE.sub(marker, RENDERED_RE.sub(rendered, text))


def filled_tokens(text: str, root: Path, inputs: set[str]) -> str:
    return TOKEN_RE.sub(lambda m: display(value_of(root, m.group(1), m.group(2), inputs)), text)


def github_links(text: str) -> str:
    """A link to a file in this repository points at it on GitHub, so it works in a PDF."""
    return LOCAL_LINK_RE.sub(lambda m: f"[{m.group(1)}]({REPO_URL}{m.group(2)})", text)


def assemble(root: Path = ROOT) -> Assembled:
    """The report's Markdown with every section and number put in. Pure: reads files only."""
    source_path = root / SOURCE
    if not source_path.is_file():
        raise ReportError(f"{SOURCE} is missing")
    inputs: set[str] = {SOURCE.as_posix()}
    out: list[str] = []
    for line in COMMENT_RE.sub("", source_path.read_text(encoding="utf-8")).splitlines():
        m = SECTION_RE.match(line.strip())
        if not m:
            out.append(line)
            continue
        rel, title = m.group(1), m.group(2)
        path = root / rel
        if not path.is_file():
            raise ReportError(f"{SOURCE} names {rel}, which does not exist")
        inputs.add(rel)
        body = section_body(path.read_text(encoding="utf-8"), title, rel)
        out.append(checked_numbers(body, root, rel, inputs))
    text = filled_tokens("\n".join(out), root, inputs)
    text = github_links(COMMENT_RE.sub("", text))
    text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"
    if "{{" in text:
        left = re.search(r"\{\{[^}]*\}\}", text)
        raise ReportError(f"a token was left in the report: {left.group(0) if left else '{{'}")
    for dash in DASHES:
        if dash in text:
            raise ReportError("the report's text has an em or en dash (hard rule 18)")
    return Assembled(text, inputs)


def sources_sha256(root: Path = ROOT, assembled: Assembled | None = None) -> str:
    """One hash over everything that decides what the PDF says and how it looks."""
    doc = assembled or assemble(root)
    parts = [doc.markdown] + [
        (root / rel).read_text(encoding="utf-8") for rel in (TEMPLATE, STYLESHEET, PRINTER)
    ]
    return sha256_text("\n\0\n".join(parts))


def pdf_pages(path: Path) -> int:
    """Page objects in the PDF. Chromium writes each page as an uncompressed /Type /Page."""
    return len(re.findall(rb"/Type\s*/Page(?!s)", path.read_bytes()))


def pandoc_version() -> str:
    exe = shutil.which("pandoc")
    if exe is None:
        raise ReportError(f"pandoc is not installed; install pandoc {PANDOC_VERSION}")
    first = subprocess.run([exe, "--version"], capture_output=True, text=True, check=True)
    version = first.stdout.splitlines()[0].strip()
    if version != f"pandoc {PANDOC_VERSION}":
        raise ReportError(
            f"{version} is installed, and the report is pinned to pandoc {PANDOC_VERSION}; "
            "install that version, or change PANDOC_VERSION in scripts/build_report.py and "
            "build the report again"
        )
    return version


def to_html_fragment(markdown: str) -> str:
    """GitHub flavoured Markdown to an HTML fragment. gfm in pandoc has no smart punctuation."""
    run = subprocess.run(
        ["pandoc", "--from", "gfm-smart", "--to", "html5", "--wrap=none"],
        input=markdown,
        capture_output=True,
        text=True,
    )
    if run.returncode != 0:
        raise ReportError(f"pandoc failed: {run.stderr.strip()}")
    return run.stdout


def font_faces(root: Path) -> str:
    """The Atkinson fonts from apps/web's node_modules, by file URL, so the PDF embeds them."""
    faces = [
        (
            "Atkinson Hyperlegible Next",
            "next",
            "atkinson-hyperlegible-next-latin-wght-normal.woff2",
            "200 800",
            "normal",
        ),
        (
            "Atkinson Hyperlegible Next",
            "next",
            "atkinson-hyperlegible-next-latin-wght-italic.woff2",
            "200 800",
            "italic",
        ),
        (
            "Atkinson Hyperlegible Mono",
            "mono",
            "atkinson-hyperlegible-mono-latin-400-normal.woff2",
            "400",
            "normal",
        ),
    ]
    css = []
    for family, key, name, weight, style in faces:
        path = root / FONT_DIRS[key] / "files" / name
        if not path.is_file():
            raise ReportError(
                f"font missing: {path.relative_to(root)}; run (cd apps/web && npm ci)"
            )
        css.append(
            f'@font-face {{ font-family: "{family}"; src: url("{path.as_uri()}") format("woff2"); '
            f"font-weight: {weight}; font-style: {style}; }}"
        )
    return "\n".join(css)


def page_html(root: Path, fragment: str) -> str:
    template = (root / TEMPLATE).read_text(encoding="utf-8")
    css = (root / STYLESHEET).read_text(encoding="utf-8")
    html = (
        template.replace("@@FONTS@@", font_faces(root))
        .replace("@@CSS@@", css)
        .replace("@@BODY@@", fragment)
    )
    if any(d in html for d in DASHES):
        raise ReportError("the report's HTML has an em or en dash (hard rule 18)")
    return html


def package_version(root: Path, rel: Path) -> str:
    doc = json.loads((root / rel / "package.json").read_text(encoding="utf-8"))
    return str(doc["version"])


def print_pdf(root: Path, html: Path, pdf: Path) -> str:
    web = root / "apps" / "web"
    playwright = web / "node_modules" / "playwright-core"
    if not playwright.is_dir():
        raise ReportError("apps/web has no node_modules; run (cd apps/web && npm ci)")
    found = package_version(root, playwright.relative_to(root))
    if found != PLAYWRIGHT_VERSION:
        raise ReportError(f"playwright-core {found} in apps/web, pinned to {PLAYWRIGHT_VERSION}")
    run = subprocess.run(
        ["node", str(root / PRINTER), str(html), str(pdf)], cwd=web, capture_output=True, text=True
    )
    if run.returncode != 0 or not pdf.is_file():
        raise ReportError(f"printing failed: {(run.stderr or run.stdout).strip()}")
    return str(json.loads(run.stdout.strip().splitlines()[-1])["browser"])


def stamp_problems(root: Path = ROOT) -> list[str]:
    """What is wrong with the committed PDF and its stamp, in plain words. Empty when current."""
    stamp_path, pdf = root / STAMP, root / PDF
    if not pdf.is_file():
        return [f"{PDF} does not exist; run make report-pdf"]
    if not stamp_path.is_file():
        return [f"{STAMP} does not exist; run make report-pdf"]
    stamp = json.loads(stamp_path.read_text(encoding="utf-8"))
    problems = []
    pages = pdf_pages(pdf)
    if not MIN_PAGES <= pages <= MAX_PAGES:
        problems.append(f"{PDF} has {pages} pages, not {MIN_PAGES} to {MAX_PAGES}")
    if stamp.get("pages") != pages:
        problems.append(f"the stamp says {stamp.get('pages')} pages and the PDF has {pages}")
    if stamp.get("pdf_sha256") != hashlib.sha256(pdf.read_bytes()).hexdigest():
        problems.append(f"{PDF} is not the file its stamp describes; run make report-pdf")
    try:
        now = sources_sha256(root)
    except ReportError as exc:
        return [*problems, f"the report's sources cannot be assembled: {exc}"]
    if stamp.get("sources_sha256") != now:
        problems.append(
            f"{PDF} was built from older sources: a README section, a doc or a result it "
            "quotes has changed since; run make report-pdf"
        )
    return problems


def build(root: Path = ROOT) -> dict[str, object]:
    pandoc = pandoc_version()
    doc = assemble(root)
    with tempfile.TemporaryDirectory(prefix="second-look-report-") as tmp:
        html = Path(tmp) / "report.html"
        html.write_text(page_html(root, to_html_fragment(doc.markdown)), encoding="utf-8")
        out = Path(tmp) / "REPORT.pdf"
        browser = print_pdf(root, html, out)
        pages = pdf_pages(out)
        if not MIN_PAGES <= pages <= MAX_PAGES:
            raise ReportError(
                f"the report came out at {pages} pages, not {MIN_PAGES} to {MAX_PAGES}"
            )
        (root / PDF).write_bytes(out.read_bytes())
    stamp: dict[str, object] = {
        "generated_by": "make report-pdf: scripts/build_report.py",
        "pdf": PDF.as_posix(),
        "pages": pages,
        "pdf_sha256": hashlib.sha256((root / PDF).read_bytes()).hexdigest(),
        "sources_sha256": sources_sha256(root, doc),
        "sources": sorted(
            doc.inputs | {TEMPLATE.as_posix(), STYLESHEET.as_posix(), PRINTER.as_posix()}
        ),
        "pandoc": pandoc,
        "browser": browser,
        "playwright": PLAYWRIGHT_VERSION,
        "fonts": {
            FONT_DIRS[k].name: package_version(root, FONT_DIRS[k]) for k in sorted(FONT_DIRS)
        },
    }
    (root / STAMP).write_text(json.dumps(stamp, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return stamp


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail when the PDF is out of date")
    args = parser.parse_args(argv)
    if args.check:
        problems = stamp_problems()
        for p in problems:
            print(f"report-pdf: {p}")
        if not problems:
            print(f"report-pdf: {PDF} is current with its sources")
        return 1 if problems else 0
    try:
        stamp = build()
    except ReportError as exc:
        print(f"report-pdf: {exc}")
        return 1
    print(f"report-pdf: {PDF}, {stamp['pages']} pages, stamp in {STAMP}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
