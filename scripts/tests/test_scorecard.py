"""docs/JUDGE_SCORECARD.md points judges at README sections by name: each name must exist."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def readme_headings() -> set[str]:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    return {m.group(1).strip() for m in re.finditer(r"^#{2,4} (.+)$", text, re.M)}


def test_every_readme_section_the_scorecard_names_exists() -> None:
    card = (ROOT / "docs" / "JUDGE_SCORECARD.md").read_text(encoding="utf-8")
    named = re.findall(r"README, ([^;|.]+[?]?)", card)
    assert named, "the scorecard names no README section"
    missing = [n.strip() for n in named if n.strip() not in readme_headings()]
    assert not missing, missing


def test_the_scorecard_does_not_wait_for_a_run_that_is_done() -> None:
    card = (ROOT / "docs" / "JUDGE_SCORECARD.md").read_text(encoding="utf-8")
    assert "arrive with the paid run" not in card
    assert "still to come" not in card


def test_the_docs_speak_with_one_voice_on_recruiting() -> None:
    """The panel may add sessions, so no public doc may say recruitment was dropped or absent."""
    stale = ("Recruitment was dropped", "no recruited study", "Nobody is recruited")
    # The dated logs keep what was true on their day: the deviations and the handoff notes.
    logs = {"deviations.md", "HANDOFF_NEXT.md", "DECISIONS.md"}
    docs = [
        ROOT / "README.md",
        *sorted(p for p in (ROOT / "docs").glob("*.md") if p.name not in logs),
    ]
    docs += [ROOT / "docs" / "submission" / "JUDGE_QA.md", ROOT / "docs" / "report" / "source.md"]
    hits = [
        f"{p.relative_to(ROOT)}: {s}"
        for p in docs
        for s in stale
        if s.lower() in p.read_text(encoding="utf-8").lower()
    ]
    assert not hits, hits
