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


def test_the_docs_say_what_the_bay_area_pack_says() -> None:
    # R01: the list was approved on Sep 25, and four pages still called it a draft waiting for one
    # person, one with a proof path that no longer existed.
    import yaml

    pack = yaml.safe_load(text(ROOT / "content" / "regions" / "california-bay-area.yaml"))
    about = {
        f"{p.relative_to(ROOT)}: {s}": s
        for p in JUDGE_PAGES
        for s in sentences(text(p))
        if "Bay Area" in s and re.search(r"\blist\b", s)
    }
    assert about, "no page says anything about the Bay Area list"
    if pack.get("approved") is True:
        stale = [k for k, s in about.items() if re.search(r"\bdraft\b|\bwaits? (on|for)\b", s)]
        assert stale == [], stale
        date = str(pack["approved_by"]).rsplit(", ", 1)[-1]
        readme = [s for s in sentences(text(README)) if "Bay Area" in s and "approved" in s]
        assert any(date in s for s in readme), f"the README never says the list was approved {date}"
    else:
        claimed = [k for k, s in about.items() if re.search(r"\bapproved for the team\b", s)]
        assert claimed == [], claimed


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


def test_the_judge_mode_risk_row_says_what_happens_after_the_lock() -> None:
    # R03: the row said only what stops the leak before the lock; the key can be rebuilt after it.
    readme = text(README)
    row = next(
        ln for ln in readme.splitlines() if ln.startswith("| Judge mode leaks the answer key")
    )
    assert "Before the lock" in row and "After the lock" in row, row
    assert "docs/THREAT_MODEL.md" in row
    weak = section(readme, "Known weaknesses")
    assert "The answer key can be rebuilt after the lock" in weak


def test_the_first_mention_of_an_arm_says_what_an_arm_is() -> None:
    # R04: half the people get the photos before the lesson, and "arm" was never explained.
    lines = text(README).splitlines()
    first = next(ln for ln in lines if re.search(r"\barms?\b", ln, re.I))
    assert "called arms" in first or first.startswith("- **Arm:**"), first


def test_the_for_judges_section_links_the_pages_written_for_judges() -> None:
    # R12: the judge's day and the twenty hardest questions were linked from nowhere a judge reads.
    judges = section(text(README), "For judges")
    for page in ("docs/JUDGE_DAY.md", "docs/submission/JUDGE_QA.md", "docs/KNOWN_BUGS.md"):
        assert f"({page})" in judges, page


def test_no_public_page_says_the_public_counts_read_zero() -> None:
    # Since 2026-09-25T17:48:55Z the public counts read 1 randomized and 1 completed: our own judge
    # walk's sitting, which the plan's exclusions leave out (docs/deviations.md). A page may still
    # say nobody has taken the test, which stays true of people.
    counts_zero = re.compile(r"\bcounts?\b[^.;]*?\b(?:reads?|shows?)\s+(?:0|zero)\b", re.I)
    said = [
        f"{p.relative_to(ROOT)}: {s}"
        for p in JUDGE_PAGES
        for s in sentences(text(p))
        if counts_zero.search(s)
    ]
    assert said == [], said
    log = text(ROOT / "docs" / "deviations.md")
    assert "2026-09-25T17:48:55Z" in log, "the judge walk's sitting is not in the deviations log"
