"""Fill README claim tokens from results/ and stamp the claim markers with values (rule 12).

Tokens: `{{claim:results/file.json#/json/pointer}}` on first render, which becomes
`<!--v:results/file.json#/json/pointer-->value<!--/v-->` so a later render can replace it.
Markers: `<!-- claim: results/file.json#/json/pointer -->` gain ` = value` so that
scripts/verify_claims.py compares the README with the results file in CI. Booleans render
as "passed" or "did not pass".
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKEN_RE = re.compile(r"\{\{claim:([\w./-]+#[\w/. -]+)\}\}")
RENDERED_RE = re.compile(r"<!--v:([\w./-]+#[\w/. -]+)-->(.*?)<!--/v-->", re.S)
MARKER_RE = re.compile(r"<!--\s*claim:\s*([\w./-]+#[\w/.-]+)\s*(?:=\s*[^\s]+)?\s*-->")


# What a line is, for broken_paragraph_lines: CommonMark's block starts, cut down to what these
# docs use. HTML_BLOCK_TAGS is CommonMark's list for HTML blocks of type 6.
FENCE_LINE_RE = re.compile(r"^ {0,3}(```|~~~)")
HEADING_LINE_RE = re.compile(r"^ {0,3}#{1,6}(\s|$)")
LIST_ITEM_RE = re.compile(r"^\s*(?:[-*+]|\d{1,9}[.)])(\s|$)")
COMMENTS_ONLY_RE = re.compile(r"^\s*(?:<!--(?:(?!-->).)*-->\s*)+$")
HTML_BLOCK_TAGS = (
    "address|article|aside|base|basefont|blockquote|body|caption|center|col|colgroup|dd|details|"
    "dialog|dir|div|dl|dt|fieldset|figcaption|figure|footer|form|frame|frameset|h1|h2|h3|h4|h5|"
    "h6|head|header|hr|html|iframe|legend|li|link|main|menu|menuitem|nav|noframes|ol|optgroup|"
    "option|p|param|search|section|summary|table|tbody|td|tfoot|th|thead|title|tr|track|ul"
)
HTML_BLOCK_RE = re.compile(rf"^ {{0,3}}</?(?:{HTML_BLOCK_TAGS})(?:\s|/?>|$)", re.I)
LONE_TAG_RE = re.compile(r"^ {0,3}(?:<[A-Za-z][\w-]*(?:\s[^<>]*)?/?>|</[A-Za-z][\w-]*\s*>)\s*$")
SENTENCE_ENDS = (".", "!", "?", '."', ".)")


def line_kinds(lines: list[str]) -> list[str]:
    """Each line as blank, text (a paragraph line), item (a list item's first line), comment (only
    comments), comment-led (starts with "<!--" and holds more), or block (anything else)."""
    kinds: list[str] = []
    fence, html, comment = False, False, False
    for line in lines:
        bare = line.strip()
        prev = kinds[-1] if kinds else "blank"
        if fence:
            kinds.append("block")
            fence = not FENCE_LINE_RE.match(line)
        elif comment:  # inside a comment that opened on an earlier line
            kinds.append("block")
            comment = "-->" not in line
        elif not bare:
            kinds.append("blank")
            html = False
        elif html:
            kinds.append("block")
        elif FENCE_LINE_RE.match(line):
            kinds.append("block")
            fence = True
        elif bare.startswith("<!--"):
            if COMMENTS_ONLY_RE.match(line):
                kinds.append("comment")
            elif "-->" not in bare:
                kinds.append("comment")
                comment = True
            else:
                kinds.append("comment-led")
        elif HTML_BLOCK_RE.match(line) or (
            LONE_TAG_RE.match(line) and prev not in ("text", "item")
        ):
            kinds.append("block")
            html = True
        elif HEADING_LINE_RE.match(line) or bare.startswith(("|", ">")):
            kinds.append("block")
        elif LIST_ITEM_RE.match(line):
            kinds.append("item")
        else:
            kinds.append("text")
    return kinds


def broken_paragraph_lines(text: str) -> list[int]:
    """Line numbers (from 1) where a line that starts with "<!--" breaks a paragraph.

    In CommonMark, and so on GitHub, a line that starts with "<!--" opens an HTML block: it cuts
    off the paragraph above it, and the rest of that line is raw HTML, so its Markdown shows as
    typed (critic round 09 L01). So a rendered number keeps a word before it on its line. A line
    that holds only a comment is fine, unless it cuts a sentence in two: paragraph text runs on
    both sides of it and the line above does not end a sentence.
    """
    lines = text.splitlines()
    kinds = line_kinds(lines)
    broken = []
    for n, kind in enumerate(kinds):
        before = kinds[n - 1] if n else "blank"
        after = kinds[n + 1] if n + 1 < len(kinds) else "blank"
        cuts = before in ("text", "item") and after == "text"
        if kind == "comment-led" or (
            kind == "comment" and cuts and not lines[n - 1].rstrip().endswith(SENTENCE_ENDS)
        ):
            broken.append(n + 1)
    return broken


def resolve(ref: str, root: Path) -> object:
    rel, pointer = ref.split("#", 1)
    doc = json.loads((root / rel).read_text(encoding="utf-8"))
    cur: object = doc
    for part in [p for p in pointer.split("/") if p]:
        if isinstance(cur, list):
            cur = cur[int(part)]
        elif isinstance(cur, dict):
            cur = cur[part]
        else:
            raise KeyError(ref)
    return cur


def display(value: object) -> str:
    if isinstance(value, bool):
        return "passed" if value else "did not pass"
    if isinstance(value, float):
        return f"{value:.1f}"
    return str(value)


def marker_value(value: object) -> str:
    """The exact string verify_claims compares with str(value) from the results file."""
    return str(value)


def render(text: str, root: Path) -> tuple[str, list[str]]:
    missing: list[str] = []

    def value_for(ref: str) -> object | None:
        try:
            return resolve(ref, root)
        except (FileNotFoundError, KeyError, IndexError, ValueError, json.JSONDecodeError):
            missing.append(ref)
            return None

    def sub_token(m: re.Match[str]) -> str:
        ref = m.group(1)
        v = value_for(ref)
        return m.group(0) if v is None else f"<!--v:{ref}-->{display(v)}<!--/v-->"

    def sub_rendered(m: re.Match[str]) -> str:
        ref = m.group(1)
        v = value_for(ref)
        return m.group(0) if v is None else f"<!--v:{ref}-->{display(v)}<!--/v-->"

    def sub_marker(m: re.Match[str]) -> str:
        ref = m.group(1)
        v = value_for(ref)
        return m.group(0) if v is None else f"<!-- claim: {ref} = {marker_value(v)} -->"

    text = RENDERED_RE.sub(sub_rendered, text)
    text = TOKEN_RE.sub(sub_token, text)
    text = MARKER_RE.sub(sub_marker, text)
    return text, sorted(set(missing))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--readme", default=str(ROOT / "README.md"))
    parser.add_argument("--check", action="store_true", help="fail if any token is unresolved")
    args = parser.parse_args()
    path = Path(args.readme)
    text, missing = render(path.read_text(encoding="utf-8"), ROOT)
    if broken := broken_paragraph_lines(text):
        for n in broken:
            print(
                f"render-readme: {path}:{n}: a line inside a paragraph starts with <!--, which "
                "breaks the paragraph on GitHub; keep a word before it on the same line"
            )
        print(f"render-readme: {path} was not written")
        return 1
    path.write_text(text, encoding="utf-8")
    unresolved = len(TOKEN_RE.findall(text))
    print(f"render-readme: {unresolved} unresolved token(s), {len(missing)} missing ref(s)")
    for ref in missing:
        print(f"  missing: {ref}")
    return 1 if (args.check and missing) else 0


if __name__ == "__main__":
    sys.exit(main())
