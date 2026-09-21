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
TOKEN_RE = re.compile(r"\{\{claim:([\w./-]+#[\w/.-]+)\}\}")
RENDERED_RE = re.compile(r"<!--v:([\w./-]+#[\w/.-]+)-->(.*?)<!--/v-->", re.S)
MARKER_RE = re.compile(r"<!--\s*claim:\s*([\w./-]+#[\w/.-]+)\s*(?:=\s*[^\s]+)?\s*-->")


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
    path.write_text(text, encoding="utf-8")
    unresolved = len(TOKEN_RE.findall(text))
    print(f"render-readme: {unresolved} unresolved token(s), {len(missing)} missing ref(s)")
    for ref in missing:
        print(f"  missing: {ref}")
    return 1 if (args.check and missing) else 0


if __name__ == "__main__":
    sys.exit(main())
