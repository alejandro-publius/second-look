"""docs/KNOWN_BUGS.md names every test marked as an expected failure, and nothing else.

Judge walk 01, R08: every test run reported "9 xfailed", and no page a judge reads said what they
were. Each is a known bug kept as a strict expected failure. The page names each by its test, and
this fails when a new mark is not on the page, or the page keeps a test whose mark is gone.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "docs" / "KNOWN_BUGS.md"
TEST_ROOTS = ("core", "apps", "evals", "scripts", "tests")
SKIP = {"node_modules", ".venv", ".next", "out"}
NAMED = re.compile(r"`((?:core|apps|evals|scripts|tests)/[\w/.-]+\.py)::(\w+)`")


def is_xfail(decorator: ast.expr) -> bool:
    """pytest.mark.xfail, called or bare."""
    target = decorator.func if isinstance(decorator, ast.Call) else decorator
    return isinstance(target, ast.Attribute) and target.attr == "xfail"


def is_strict(decorator: ast.expr) -> bool:
    return isinstance(decorator, ast.Call) and any(
        k.arg == "strict" and isinstance(k.value, ast.Constant) and k.value.value is True
        for k in decorator.keywords
    )


def marked(root: Path = ROOT) -> dict[str, bool]:
    """Every test function with an xfail mark, as path::name, and whether the mark is strict."""
    found: dict[str, bool] = {}
    for top in TEST_ROOTS:
        for path in sorted((root / top).rglob("test_*.py")) if (root / top).is_dir() else []:
            if SKIP & set(path.relative_to(root).parts):
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                    marks = [d for d in node.decorator_list if is_xfail(d)]
                    if marks:
                        key = f"{path.relative_to(root).as_posix()}::{node.name}"
                        found[key] = all(is_strict(d) for d in marks)
    return found


def named(text: str) -> set[str]:
    return {f"{path}::{name}" for path, name in NAMED.findall(text)}


def test_the_page_names_exactly_the_tests_marked_as_expected_failures() -> None:
    tests = marked()
    assert tests, "no test is marked as an expected failure, so the page should go"
    on_page = named(PAGE.read_text(encoding="utf-8"))
    assert sorted(set(tests) - on_page) == [], "marked, but not on docs/KNOWN_BUGS.md"
    assert sorted(on_page - set(tests)) == [], "on docs/KNOWN_BUGS.md, but not marked"


def test_every_expected_failure_is_strict() -> None:
    # A mark that is not strict passes quietly the day the bug is fixed, and the page goes stale.
    loose = sorted(name for name, strict in marked().items() if not strict)
    assert loose == [], loose


def test_the_readme_known_weaknesses_link_the_page() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    start = readme.index("## Known weaknesses")
    end = readme.index("\n## ", start + 1)
    assert "(docs/KNOWN_BUGS.md)" in readme[start:end]


def test_the_finder_sees_a_strict_mark_and_a_loose_one(tmp_path: Path) -> None:
    (tmp_path / "core" / "tests").mkdir(parents=True)
    (tmp_path / "core" / "tests" / "test_x.py").write_text(
        "import pytest\n\n"
        "@pytest.mark.xfail(strict=True, reason='bug')\n"
        "def test_a() -> None: ...\n\n"
        "@pytest.mark.xfail\n"
        "def test_b() -> None: ...\n\n"
        "def test_c() -> None: ...\n",
        encoding="utf-8",
    )
    assert marked(tmp_path) == {
        "core/tests/test_x.py::test_a": True,
        "core/tests/test_x.py::test_b": False,
    }
