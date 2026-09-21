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
