"""The pages a judge reads say what the code and the files say (judge walk 01).

Each test pins one finding from that walk: a sentence that had drifted from the file it describes,
or a gap a judge met. They read words, so each names the file that decides what the words must be.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"
# The public pages a judge reads. The dated logs (deviations, DECISIONS, the handoff) keep what was
# true on their day, as test_scorecard.py's recruiting test also allows.
LOGS = {"deviations.md", "DECISIONS.md", "HANDOFF_NEXT.md"}
JUDGE_PAGES = [
    README,
    ROOT / "WRITEUP.md",
    *sorted(p for p in (ROOT / "docs").glob("*.md") if p.name not in LOGS),
    ROOT / "docs" / "submission" / "JUDGE_QA.md",
    ROOT / "docs" / "report" / "source.md",
]


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def sentences(body: str) -> list[str]:
    flat = re.sub(r"\s+", " ", body)
    return [s.strip() for s in re.split(r"(?<=[.;!?])\s+|\|", flat) if s.strip()]


def section(body: str, heading: str) -> str:
    start = body.index(f"\n## {heading}\n")
    end = body.find("\n## ", start + 1)
    return body[start : end if end > 0 else len(body)]


def test_no_public_page_says_every_ai_number_is_graded_from_a_reply() -> None:
    # R02: the benchmark runs kept counts, not replies, so their counts are checked as recorded.
    said = [
        f"{p.relative_to(ROOT)}: {s}"
        for p in JUDGE_PAGES
        for s in sentences(text(p))
        if re.search(r"\bevery AI number\b", s, re.I)
    ]
    assert said == [], said


def test_the_evals_section_names_the_numbers_checked_only_as_recorded() -> None:
    evals = section(text(README), "Evals")
    line = next(ln for ln in evals.splitlines() if ln.startswith("- `make reproduce`"))
    # The three kinds of number evals/reproduce.py's benchmark note calls "as recorded".
    named = line[line.index("checked as recorded") :]
    for words in ("right-answer counts", "can't tell", "malformed"):
        assert words in named, words
