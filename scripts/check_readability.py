"""Reading age of the words on screen (hard rule 18, Update 14 section 5).

Hard rule 18 asks for plain words at a reading age of about 12. That is a Flesch-Kincaid grade
level of about 7, which is a reading age of about 12 to 13. This measures every string a person
can see and fails when one is harder than the line below, so the rule is a gate rather than an
intention.

What it measures: `content/locales/en.json`, the sentences in `content/approved_sentences.yaml`,
and the text in `content/lessons.yaml`, `content/items.yaml`, `content/form.yaml`,
`content/followups.yaml` and `content/glossary.yaml`. Nothing under `docs/` is measured: the
docs are for judges and maintainers, not for a person standing at a creek.

How it measures: Flesch-Kincaid grade level per string, over strings of at least MIN_WORDS words.
A short label such as "Next photo" has no useful grade, so it is skipped. The average over
everything must be at or under AVERAGE_MAX, and no single string may be over STRING_MAX.

Exceptions: `content/readability_exceptions.yaml`, one key per string with the reason. Keep it
short. A long list means the writing got harder, not that the rule got wrong.

Run: uv run python scripts/check_readability.py
     uv run python scripts/check_readability.py --worst 20   list the hardest strings
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
EXCEPTIONS = CONTENT / "readability_exceptions.yaml"
LOCALE = CONTENT / "locales" / "en.json"
YAML_FILES = (
    "approved_sentences.yaml",
    "lessons.yaml",
    "items.yaml",
    "form.yaml",
    "followups.yaml",
    "glossary.yaml",
)
# Keys inside the content YAML whose value is shown to a person. Everything else is plumbing.
TEXT_KEYS = {
    "text",
    "sentence",
    "question",
    "label",
    "title",
    "heading",
    "rule",
    "why",
    "reason",
    "note",
    "help",
    "plain",
    "definition",
    "feedback",
    "caption",
    "alt",
    "body",
    "answer",
}
MIN_WORDS = 12
AVERAGE_MAX = 7.0
STRING_MAX = 11.0

WORD = re.compile(r"[A-Za-z][A-Za-z'-]*")
SENTENCE_END = re.compile(r"[.!?]+")
PLACEHOLDER = re.compile(r"\{[^}]*\}")
VOWELS = "aeiouy"


def syllables(word: str) -> int:
    """A count good enough for a grade level. Errs high on long words, which is the safe way."""
    word = word.lower().strip("'-")
    if not word:
        return 0
    count = 0
    previous_was_vowel = False
    for char in word:
        is_vowel = char in VOWELS
        if is_vowel and not previous_was_vowel:
            count += 1
        previous_was_vowel = is_vowel
    if word.endswith("e") and not word.endswith(("le", "ee", "ye")) and count > 1:
        count -= 1
    return max(1, count)


def grade(text: str) -> tuple[float, int]:
    """Flesch-Kincaid grade level, and the word count it was computed from."""
    clean = PLACEHOLDER.sub("thing", text)
    words = WORD.findall(clean)
    if not words:
        return 0.0, 0
    sentences = max(1, len([p for p in SENTENCE_END.split(clean) if p.strip()]))
    total_syllables = sum(syllables(w) for w in words)
    value = 0.39 * (len(words) / sentences) + 11.8 * (total_syllables / len(words)) - 15.59
    return round(value, 2), len(words)


def walk_yaml(node: Any, where: str, out: list[tuple[str, str]]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(value, str) and key in TEXT_KEYS:
                out.append((f"{where}.{key}", value))
            else:
                walk_yaml(value, f"{where}.{key}", out)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            walk_yaml(value, f"{where}[{index}]", out)


def collect(root: Path) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    locale = root / "content" / "locales" / "en.json"
    if locale.exists():
        data = json.loads(locale.read_text(encoding="utf-8"))
        for key, value in data.items():
            if isinstance(value, str):
                out.append((f"locales/en.json:{key}", value))
    for name in YAML_FILES:
        path = root / "content" / name
        if not path.exists():
            continue
        walk_yaml(yaml.safe_load(path.read_text(encoding="utf-8")), name, out)
    return out


def load_exceptions(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {str(k): str(v) for k, v in (data.get("exceptions") or {}).items()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--worst", type=int, default=0, help="list the N hardest strings")
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    exceptions = load_exceptions(args.root / "content" / "readability_exceptions.yaml")
    scored: list[tuple[float, int, str, str]] = []
    for key, text in collect(args.root):
        value, words = grade(text)
        if words < MIN_WORDS:
            continue
        scored.append((value, words, key, text))
    if not scored:
        print("readability: nothing long enough to measure")
        return 0

    measured = [s for s in scored if s[2] not in exceptions]
    average = sum(s[0] for s in measured) / len(measured) if measured else 0.0
    too_hard = sorted((s for s in measured if s[0] > STRING_MAX), reverse=True)

    if args.worst:
        for value, words, key, text in sorted(measured, reverse=True)[: args.worst]:
            print(f"  {value:5.1f}  {words:3d} words  {key}\n         {text[:110]}")

    problems: list[str] = []
    for value, _words, key, text in too_hard:
        problems.append(f"grade {value} is over {STRING_MAX}: {key}\n    {text[:120]}")
    if average > AVERAGE_MAX:
        problems.append(f"average grade {average:.2f} is over {AVERAGE_MAX}")
    stale = [k for k in exceptions if k not in {s[2] for s in scored}]
    for key in stale:
        problems.append(f"exception for a string that is no longer there: {key}")

    if problems:
        print("\n".join(problems))
        print(f"readability: {len(problems)} problem(s) over {len(measured)} strings")
        return 1
    print(
        f"readability: {len(measured)} strings, average grade {average:.2f} "
        f"(cap {AVERAGE_MAX}), hardest {max(s[0] for s in measured):.1f} (cap {STRING_MAX}), "
        f"{len(exceptions)} exception(s)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
