"""Every decision record in docs/adr/ has its parts and a line in the index, numbered in order."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ADR = ROOT / "docs" / "adr"
RECORDS = sorted(ADR.glob("[0-9][0-9][0-9][0-9]-*.md"))
PARTS = ("## Context", "## Decision", "## Consequences", "- **Date:**", "- **Carried by:**")


def test_the_records_are_numbered_from_0001_with_no_gap() -> None:
    numbers = [int(p.name[:4]) for p in RECORDS]
    assert len(numbers) >= 8
    assert numbers == list(range(1, len(numbers) + 1))


def test_the_index_lists_every_record_once_with_its_title_and_date() -> None:
    index = (ADR / "README.md").read_text(encoding="utf-8")
    linked = re.findall(
        r"^\| \[(\d{4})\]\(([^)]+)\) \| (.+?) \| (\d{4}-\d{2}-\d{2}) \|", index, re.M
    )
    assert [f for _, f, _, _ in linked] == [p.name for p in RECORDS]
    for number, name, title, date in linked:
        text = (ADR / name).read_text(encoding="utf-8")
        assert text.startswith(f"# {number}. {title}\n"), name
        assert f"- **Date:** {date}" in text, name


@pytest.mark.parametrize("record", RECORDS, ids=lambda p: p.name)
def test_each_record_has_context_decision_consequences_date_and_carrier(record: Path) -> None:
    text = record.read_text(encoding="utf-8")
    for part in PARTS:
        assert part in text, f"{record.name}: no {part}"


@pytest.mark.parametrize("record", RECORDS, ids=lambda p: p.name)
def test_every_commit_a_record_names_is_in_this_history(record: Path) -> None:
    carried = record.read_text(encoding="utf-8").split("- **Carried by:**", 1)[1].split("\n## ")[0]
    commits = re.findall(r"commit ([0-9a-f]{7,40})\b", carried)
    assert commits, f"{record.name} names no commit"
    for sha in commits:
        done = subprocess.run(
            ["git", "cat-file", "-e", f"{sha}^{{commit}}"], cwd=ROOT, capture_output=True
        )
        assert done.returncode == 0, f"{record.name}: {sha} is not a commit here"
