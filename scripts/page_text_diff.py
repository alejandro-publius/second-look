"""Every word a person can see or hear on two static exports of the web app, compared page by page.

Update 22 section 1 answer 2: the smaller warm-up photo copies change markup only, and the proof is
a diff of the strings that comes out empty. For each .html page of each export this reads the text
outside script, style, template and noscript, plus the attributes that are read out or shown: alt,
aria-label, aria-description, title, placeholder, label, and the page's description. Markup,
class names, file names and the payload scripts are not strings a person sees, so they are left
out.

    cd apps/web && NEXT_PUBLIC_API_ORIGIN="" npm run export     once at each commit, copying out/
    uv run python scripts/page_text_diff.py <before out/> <after out/>

Prints nothing but a count and exits 0 when every page says the same thing; prints the diff and
exits 1 when any string or any page differs.
"""

from __future__ import annotations

import argparse
import difflib
import sys
from html.parser import HTMLParser
from pathlib import Path

HIDDEN = {"script", "style", "template", "noscript"}
READ_OUT = ("alt", "aria-label", "aria-description", "title", "placeholder", "label")
META = {"description", "og:title", "og:description"}


class _Words(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lines: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: v for k, v in attrs if v}
        for name in READ_OUT:
            if name in a:
                self.lines.append(f"[{tag} {name}] {' '.join(a[name].split())}")
        meta = a.get("name") or a.get("property")
        if tag == "meta" and meta in META and "content" in a:
            self.lines.append(f"[meta {meta}] {' '.join(a['content'].split())}")
        if tag in HIDDEN:
            self.hidden += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag in HIDDEN:
            self.hidden -= 1

    def handle_endtag(self, tag: str) -> None:
        if tag in HIDDEN and self.hidden:
            self.hidden -= 1

    def handle_data(self, data: str) -> None:
        if not self.hidden and data.strip():
            self.lines.append(" ".join(data.split()))


def page_words(html: str) -> list[str]:
    """The strings of one page, in page order, one per line."""
    parser = _Words()
    parser.feed(html)
    parser.close()
    return parser.lines


def pages(root: Path) -> dict[str, Path]:
    return {p.relative_to(root).as_posix(): p for p in sorted(root.rglob("*.html"))}


def compare(before: Path, after: Path) -> tuple[list[str], int]:
    """The diff lines between the two exports, and how many pages both have."""
    old, new = pages(before), pages(after)
    out: list[str] = []
    for rel in sorted(old.keys() - new.keys()):
        out.append(f"only in before: {rel}")
    for rel in sorted(new.keys() - old.keys()):
        out.append(f"only in after: {rel}")
    both = sorted(old.keys() & new.keys())
    for rel in both:
        a = page_words(old[rel].read_text(encoding="utf-8"))
        b = page_words(new[rel].read_text(encoding="utf-8"))
        if a != b:
            out.extend(difflib.unified_diff(a, b, f"before/{rel}", f"after/{rel}", lineterm=""))
    return out, len(both)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("before", type=Path, help="the out/ folder of the earlier export")
    parser.add_argument("after", type=Path, help="the out/ folder of the later export")
    args = parser.parse_args(argv)
    for root in (args.before, args.after):
        if not (root / "index.html").exists():
            print(f"page-text-diff: no static export in {root}")
            return 1
    diff, count = compare(args.before, args.after)
    if diff:
        print("\n".join(diff))
        print(f"page-text-diff: strings differ ({len(diff)} diff lines over {count} pages)")
        return 1
    print(f"page-text-diff: {count} pages, the same strings on every one")
    return 0


if __name__ == "__main__":
    sys.exit(main())
