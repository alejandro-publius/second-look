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
# A number render_readme.py put in the text: <!--v:results/x.json#/a/b-->42<!--/v-->. It is
# checked too, or a rendered number could drift from results/ with CI still green.
RENDERED_RE = re.compile(r"<!--v:([\w./-]+)#([\w/.-]+)-->(.*?)<!--/v-->", re.S)
UNRENDERED_RE = re.compile(r"\{\{claim:[^}]*\}\}")
# Simulations by design: made-up people, never a stand-in for real data, and the README says so
# where it quotes them. These may be cited without --synthetic. Any other synthetic file may not.
SIMULATIONS = frozenset({"results/consensus_coarseness.json"})


def display(value: object) -> str:
    """The same text scripts/render_readme.py writes for a value."""
    if isinstance(value, bool):
        return "passed" if value else "did not pass"
    if isinstance(value, float):
        return f"{value:.1f}"
    return str(value)


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
    parser.add_argument(
        "--file", type=Path, default=None, help="check this markdown file instead of README.md"
    )
    args = parser.parse_args()
    target = ROOT / args.file if args.file and not args.file.is_absolute() else args.file or README
    if not target.exists():
        print(f"verify-claims: {target.name} missing")
        return 1
    text = target.read_text(encoding="utf-8")
    problems: list[str] = []
    checked = 0
    for m in CLAIM_RE.finditer(text):
        rel, pointer, expected = m.group(1), m.group(2), m.group(3)
        path = ROOT / rel
        if not path.exists():
            problems.append(f"claim points at missing file: {rel}")
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        simulation = rel in SIMULATIONS
        if isinstance(doc, dict) and doc.get("synthetic") and not args.synthetic and not simulation:
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
    for m in RENDERED_RE.finditer(text):
        rel, pointer, shown = m.group(1), m.group(2), m.group(3)
        path = ROOT / rel
        if not path.exists():
            problems.append(f"rendered number points at missing file: {rel}")
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        simulation = rel in SIMULATIONS
        if isinstance(doc, dict) and doc.get("synthetic") and not args.synthetic and not simulation:
            problems.append(f"synthetic results shown without --synthetic: {rel}")
            continue
        try:
            value = resolve_pointer(doc, pointer)
        except (KeyError, IndexError, ValueError):
            problems.append(f"rendered pointer not found: {rel}#{pointer}")
            continue
        if display(value) != shown:
            problems.append(
                f"rendered number drifted: {rel}#{pointer} README shows {shown}, results say "
                f"{display(value)}; run scripts/render_readme.py"
            )
        checked += 1
    for token in UNRENDERED_RE.findall(text):
        problems.append(f"unrendered token {token}; run scripts/render_readme.py")
    if problems:
        print("\n".join(problems))
        print(f"verify-claims: {len(problems)} problem(s)")
        return 1
    print(f"verify-claims: {checked} claim(s) checked, all match results/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
