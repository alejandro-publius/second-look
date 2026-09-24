"""scripts/count_tests.py reads each tool's own output. These pin how it reads it."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import count_tests as tc

ROOT = Path(__file__).resolve().parents[2]


def test_pytest_per_file_lines_are_summed() -> None:
    out = "core/tests/test_gate.py: 41\ncore/tests/test_lock.py: 5\n\nscripts/tests/test_x.py: 3\n"
    assert tc.parse_pytest(out) == {"tests": 49, "files": 3}


def test_pytest_per_test_lines_are_counted_by_file() -> None:
    out = (
        "core/tests/test_lock.py::test_a\ncore/tests/test_lock.py::test_b[1]\n"
        "evals/tests/test_power.py::test_c\n\n3 tests collected in 0.5s\n"
    )
    assert tc.parse_pytest(out) == {"tests": 3, "files": 2}


def test_pytest_totals_that_disagree_are_refused() -> None:
    with pytest.raises(tc.CountError):
        tc.parse_pytest("core/tests/test_lock.py::test_a\n7 tests collected in 0.1s\n")


def test_pytest_output_with_no_file_is_refused() -> None:
    with pytest.raises(tc.CountError):
        tc.parse_pytest("ERROR: file or directory not found\n")


def test_playwright_total_line_is_read() -> None:
    out = "Listing tests:\n  a.spec.ts:1:1 > one\nTotal: 57 tests in 15 files\n"
    assert tc.parse_playwright(out) == {"tests": 57, "spec_files": 15}


def test_playwright_listing_nothing_is_refused() -> None:
    with pytest.raises(tc.CountError):
        tc.parse_playwright("Error: no content\nTotal: 0 tests in 0 files\n")
    with pytest.raises(tc.CountError):
        tc.parse_playwright("something else\n")


def test_golden_cases_count_every_top_level_list(tmp_path: Path) -> None:
    (tmp_path / "a.json").write_text(json.dumps({"function": "f", "cases": [1, 2, 3]}))
    (tmp_path / "b.json").write_text(json.dumps({"x": [1], "y": [1, 2], "note": "n"}))
    test_file = tmp_path / "golden.test.ts"
    test_file.write_text('test("one", () => {});\n  test("two", () => {});\n// test("no")\n')
    assert tc.count_golden(tmp_path, test_file) == {"cases": 6, "files": 2, "node_tests": 2}


def test_e2e_sections_start_after_the_server_is_up() -> None:
    text = (
        'at("apply schema and arms");\nat("start wrangler dev");\n'
        '  at("sessions and visits");\n  at("the record");\n'
    )
    assert tc.e2e_sections(text) == ["sessions and visits", "the record"]


def test_e2e_file_without_its_set_up_steps_is_refused() -> None:
    with pytest.raises(tc.CountError):
        tc.e2e_sections('at("the record");\n')


def test_the_real_golden_files_and_e2e_are_read() -> None:
    golden = tc.count_golden(tc.GOLDEN_DIR, tc.GOLDEN_TEST)
    assert golden["files"] >= 8 and golden["cases"] > golden["files"]
    assert golden["node_tests"] > 0
    assert "the record" in tc.e2e_sections(tc.E2E.read_text(encoding="utf-8"))


def test_the_committed_counts_have_every_field_the_readme_cites() -> None:
    counts = json.loads((ROOT / "results" / "test_counts.json").read_text(encoding="utf-8"))
    assert counts["synthetic"] is False
    for pointer in (
        ("python", "tests"),
        ("worker_golden", "cases"),
        ("worker_golden", "node_tests"),
        ("playwright", "tests"),
        ("playwright", "spec_files"),
        ("worker_e2e", "sections"),
    ):
        value = counts[pointer[0]][pointer[1]]
        assert isinstance(value, int) and value > 0, pointer
