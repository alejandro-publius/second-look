import json
from pathlib import Path

from scripts.render_readme import render


def test_render_fills_tokens_and_stamps_markers(tmp_path: Path) -> None:
    (tmp_path / "results").mkdir()
    (tmp_path / "results" / "r.json").write_text(
        json.dumps({"primary": {"mean": 61.25}, "m": {"x": True}})
    )
    text = (
        "<!-- claim: results/r.json#/primary/mean -->\n"
        "| a | {{claim:results/r.json#/primary/mean}} | {{claim:results/r.json#/m/x}} |\n"
    )
    out, missing = render(text, tmp_path)
    assert missing == []
    assert "<!-- claim: results/r.json#/primary/mean = 61.25 -->" in out
    assert "<!--v:results/r.json#/primary/mean-->61.2<!--/v-->" in out or "61.3<!--/v-->" in out
    assert "<!--v:results/r.json#/m/x-->passed<!--/v-->" in out
    # a second render with a new value replaces the rendered value in place
    (tmp_path / "results" / "r.json").write_text(
        json.dumps({"primary": {"mean": 70.0}, "m": {"x": False}})
    )
    out2, _ = render(out, tmp_path)
    assert "70.0<!--/v-->" in out2 and "did not pass<!--/v-->" in out2
    assert "= 70.0 -->" in out2


def test_missing_file_leaves_token_and_reports(tmp_path: Path) -> None:
    out, missing = render("{{claim:results/none.json#/a}}", tmp_path)
    assert out == "{{claim:results/none.json#/a}}"
    assert missing == ["results/none.json#/a"]


def test_every_doc_with_a_rendered_number_is_rendered_and_checked() -> None:
    """Critic round 07 J01: test_counts.json moved, the README was rendered again, and WRITEUP.md
    and docs/ACCEPTANCE.md kept the old counts, so CI went red on main. Every tracked doc that
    holds a rendered value must be in the Makefile's RENDERED_DOCS and checked by verify-claims."""
    import re
    import subprocess

    root = Path(__file__).resolve().parents[2]
    tracked = subprocess.run(
        ["git", "ls-files", "*.md"], cwd=root, capture_output=True, text=True, check=True
    ).stdout.split()
    marked = {
        p for p in tracked if "<!--v:" in (root / p).read_text(encoding="utf-8", errors="ignore")
    }
    make = (root / "Makefile").read_text(encoding="utf-8")
    rendered = set(re.search(r"^RENDERED_DOCS := (.+)$", make, re.M).group(1).split())
    checked = set(re.findall(r"verify_claims\.py --file (\S+)", make))
    marked.discard("README.md")  # render_readme.py and verify_claims.py take it by default
    assert marked, "no doc with a rendered value was found"
    assert sorted(marked - rendered) == [], "rendered values that make render-readme misses"
    assert sorted(marked - checked) == [], "rendered values that make verify-claims misses"
