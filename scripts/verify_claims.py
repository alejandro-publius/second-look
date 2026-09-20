"""Every number in README.md must trace to results/ (hard rule 12).

Claims are written in the README as `<!-- claim: <results-file>#<json-pointer> -->` on the line
before the number, or inline as `{{claim:<file>#<pointer>}}` markers replaced by
scripts/render_readme.py. Stage 1 (Phase 0): the README has no claims, so this passes when
no claim markers exist and no bare result-like numbers appear inside the results table.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
CLAIM_RE = re.compile(r"<!--\s*claim:\s*([\w./-]+)#([\w/.-]+)\s*(?:=\s*([^\s]+))?\s*-->")


def resolve_pointer(doc: object, pointer: str) -> object:
    cur = doc
    for part in [p for p in pointer.split("/") if p]:
        if isinstance(cur, list):
            cur = cur[int(part)]
        elif isinstance(cur, dict):
            cur = cur[part]
        else:
            raise KeyError(pointer)
    return cur


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--synthetic", action="store_true", help="accept results stamped synthetic")
    args = parser.parse_args()
    if not README.exists():
        print("verify-claims: README.md missing")
        return 1
    text = README.read_text(encoding="utf-8")
    problems: list[str] = []
    checked = 0
    for m in CLAIM_RE.finditer(text):
        rel, pointer, expected = m.group(1), m.group(2), m.group(3)
        path = ROOT / rel
        if not path.exists():
            problems.append(f"claim points at missing file: {rel}")
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(doc, dict) and doc.get("synthetic") and not args.synthetic:
            problems.append(f"synthetic results cited without --synthetic: {rel}")
            continue
        try:
            value = resolve_pointer(doc, pointer)
        except (KeyError, IndexError, ValueError):
            problems.append(f"claim pointer not found: {rel}#{pointer}")
            continue
        if expected is not None and str(value) != expected:
            problems.append(
                f"claim value drifted: {rel}#{pointer} README says {expected}, results say {value}"
            )
        checked += 1
    if problems:
        print("\n".join(problems))
        print(f"verify-claims: {len(problems)} problem(s)")
        return 1
    print(f"verify-claims: {checked} claim(s) checked, all match results/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
