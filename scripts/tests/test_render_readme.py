import json
from pathlib import Path

import pytest

from scripts.render_readme import broken_paragraph_lines, render


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
    # A whole rendered value, outside code spans: a review that quotes "`<!--v:`" is not one.
    value = re.compile(r"<!--v:[^\s>]+-->[^<]*<!--/v-->")
    marked = {
        p
        for p in tracked
        if value.search(
            re.sub(r"`[^`]*`", "", (root / p).read_text(encoding="utf-8", errors="ignore"))
        )
    }
    make = (root / "Makefile").read_text(encoding="utf-8")
    found = re.search(r"^RENDERED_DOCS := (.+)$", make, re.M)
    assert found, "the Makefile has no RENDERED_DOCS line"
    rendered = set(found.group(1).split())
    checked = set(re.findall(r"verify_claims\.py --file (\S+)", make))
    marked.discard("README.md")  # render_readme.py and verify_claims.py take it by default
    assert marked, "no doc with a rendered value was found"
    assert sorted(marked - rendered) == [], "rendered values that make render-readme misses"
    assert sorted(marked - checked) == [], "rendered values that make verify-claims misses"


def headings_inside_folds(text: str) -> list[str]:
    """Headings that sit inside an open <details>, where GitHub hides them until the fold opens."""
    import re

    depth, hidden, fence = 0, [], False
    for n, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            fence = not fence
            continue
        if fence:
            continue
        tags = re.sub(r"`[^`]*`", "", line)  # a tag named in a code span is prose, not a fold
        depth += len(re.findall(r"<details\b", tags)) - len(re.findall(r"</details>", tags))
        if depth > 0 and re.match(r"#{1,6} ", line):
            hidden.append(f"{n}: {line}")
    return hidden


def test_no_heading_hides_inside_a_fold() -> None:
    """Critic round 08 K01: a fold's closing tag landed two sections too low, and GitHub hid "Why
    trust a volunteer, and the AI?" and "What the AI cannot do" inside the lesson photos' fold.
    A fold holds a table or a picture, never a section, in any tracked Markdown file."""
    import subprocess

    root = Path(__file__).resolve().parents[2]
    tracked = subprocess.run(
        ["git", "ls-files", "*.md"], cwd=root, capture_output=True, text=True, check=True
    ).stdout.split()
    texts = {p: (root / p).read_text(encoding="utf-8", errors="ignore") for p in tracked}
    found = {p: hidden for p, text in texts.items() if (hidden := headings_inside_folds(text))}
    assert found == {}


def test_the_fold_check_sees_a_heading_inside_a_fold() -> None:
    assert headings_inside_folds("<details>\n<summary>a</summary>\n\n## B\n\n</details>\n") == [
        "4: ## B"
    ]
    assert headings_inside_folds("<details>\n\n| a |\n\n</details>\n\n## B\n") == []
    assert headings_inside_folds("```\n<details>\n```\n## B\n") == []
    assert headings_inside_folds("A `<details>` block.\n\n## B\n") == []


def test_no_paragraph_line_starts_with_a_comment() -> None:
    """Critic round 09 L01: in CommonMark a line that starts with "<!--" opens an HTML block, so
    GitHub cut 21 paragraphs of the README, the WRITEUP and the two cards short and showed the
    rest of each line as typed. A rendered number keeps a word before it on its line."""
    import subprocess

    root = Path(__file__).resolve().parents[2]
    tracked = subprocess.run(
        ["git", "ls-files", "*.md"], cwd=root, capture_output=True, text=True, check=True
    ).stdout.split()
    texts = {p: (root / p).read_text(encoding="utf-8", errors="ignore") for p in tracked}
    found = {p: broken for p, text in texts.items() if (broken := broken_paragraph_lines(text))}
    assert found == {}


def test_the_paragraph_check_sees_a_comment_that_breaks_a_paragraph() -> None:
    v = "<!--v:results/r.json#/n-->3<!--/v-->"
    # a rendered number at the start of a line inside a paragraph, or of a paragraph
    assert broken_paragraph_lines(f"The gate saw\n{v} flags.\n") == [2]
    assert broken_paragraph_lines(f"{v} phone screens.\n") == [1]
    # the same inside a list item, where the line is indented
    assert broken_paragraph_lines(f"- It saw\n  {v} flags.\n") == [2]
    # two rendered numbers on a line are not one long comment
    assert broken_paragraph_lines(f"From\n{v} to {v}\n") == [2]
    # a number with a word before it holds the paragraph together
    assert broken_paragraph_lines(f"The gate\nsaw {v} flags.\n") == []
    # a claim comment alone between blank lines, or after a full stop, is fine
    claim = "<!-- claim: results/r.json#/n = 3 -->"
    assert broken_paragraph_lines(f"Text.\n\n{claim}\n{claim}\n\nMore.\n") == []
    assert broken_paragraph_lines(f"It is real.\n{claim}\nProof: a file.\n") == []
    # but not in the middle of a sentence
    assert broken_paragraph_lines(f"The gate kept\n{claim}\n35 flags.\n") == [2]
    # a comment in a code fence, a table cell or an HTML block is not a paragraph line
    assert broken_paragraph_lines(f"```\nText\n{v} x\n```\n") == []
    assert broken_paragraph_lines(f"| a |\n|---|\n| {v} |\n") == []
    assert broken_paragraph_lines(f"<table>\n<tr><td>\n{v} x\n</td></tr>\n</table>\n") == []


def test_render_refuses_to_write_a_line_that_breaks_a_paragraph(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    import scripts.render_readme as rr

    doc = tmp_path / "DOC.md"
    before = "The gate saw\n<!--v:results/r.json#/n-->3<!--/v--> flags.\n"
    doc.write_text(before, encoding="utf-8")
    (tmp_path / "results").mkdir()
    (tmp_path / "results" / "r.json").write_text(json.dumps({"n": 4}))
    monkeypatch.setattr(rr, "ROOT", tmp_path)
    monkeypatch.setattr("sys.argv", ["render_readme.py", "--readme", str(doc)])
    assert rr.main() == 1
    assert doc.read_text(encoding="utf-8") == before, "a doc with a broken line must stay as it was"
    assert f"{doc}:2:" in capsys.readouterr().out
    doc.write_text(before.replace("saw\n", "saw "), encoding="utf-8")
    assert rr.main() == 0
    assert "saw <!--v:results/r.json#/n-->4<!--/v--> flags." in doc.read_text(encoding="utf-8")
