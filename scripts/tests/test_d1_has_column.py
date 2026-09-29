"""The deploy's question to the live database: is the column there, missing, or unreadable?"""

from __future__ import annotations

import io
import json
import re
from pathlib import Path

import pytest

from scripts import d1_has_column as d

ROOT = Path(__file__).resolve().parents[2]


def answer(*names: str, success: bool = True) -> str:
    rows = [{"name": n} for n in names]
    return json.dumps([{"results": rows, "success": success, "meta": {"served_by": "v3"}}])


def test_present_missing_and_unreadable_are_three_different_answers() -> None:
    assert d.state(answer("visit_id", "language"), "language") == d.PRESENT
    assert d.state(answer("visit_id", "kind"), "language") == d.MISSING
    for text in ("", "not json", "[", "{}", "[]", '[{"results": "x"}]', '[{"results": [{}]}]'):
        assert d.state(text, "language") == d.UNREADABLE, text


def test_a_failed_query_or_a_table_with_no_column_is_unreadable_never_missing() -> None:
    assert d.state(answer("visit_id", success=False), "language") == d.UNREADABLE
    assert d.state(answer(), "language") == d.UNREADABLE


def test_words_before_the_json_are_skipped() -> None:
    notice = " wrangler 4.135.0 (update available 4.141.0)\n-----\n"
    assert d.state(notice + answer("language"), "language") == d.PRESENT
    assert d.state(notice + answer("kind"), "language") == d.MISSING


def test_a_column_is_matched_whole_not_as_part_of_another_name() -> None:
    assert d.state(answer("language_code", "languages"), "language") == d.MISSING


def test_the_command_reads_stdin_and_exits_with_the_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO(answer("language")))
    assert d.main(["language"]) == d.PRESENT
    monkeypatch.setattr("sys.stdin", io.StringIO("nothing"))
    assert d.main(["language"]) == d.UNREADABLE
    assert d.main([]) == d.UNREADABLE


def test_deploy_adds_the_column_only_when_missing_and_stops_when_unreadable() -> None:
    text = (ROOT / "scripts" / "deploy.sh").read_text(encoding="utf-8")
    assert "scripts/d1_has_column.py language" in text
    block = text[text.index("d1_has_column.py") :]
    block = block[: block.index("wrangler deploy")]
    # 1 runs the migration, anything else but 0 stops the deploy before the Worker goes up.
    assert re.search(r"1\)\s*\n?.*migrations/0001_visit_language\.sql", block, re.S)
    assert re.search(r"\*\)\s*\n?.*exit 1", block, re.S)
