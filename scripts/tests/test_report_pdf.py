"""docs/REPORT.pdf exists, has 4 to 10 pages, and was built from the sources as they are now.

The build needs pandoc and Chromium; this test needs neither. It assembles the report's Markdown
again from docs/report/source.md, the README and docs sections it names and results/, hashes it
with the template, the stylesheet and the print script, and compares that with the stamp that
`make report-pdf` wrote in results/report_pdf.json. A section or a result that changed after the
PDF was built fails here until the PDF is built again.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path

import pytest

from scripts import build_report as br

ROOT = Path(__file__).resolve().parents[2]


# The committed PDF ------------------------------------------------------------------------------


def test_the_pdf_exists_and_has_four_to_ten_pages() -> None:
    pdf = ROOT / br.PDF
    assert pdf.is_file(), "docs/REPORT.pdf is missing; run make report-pdf"
    assert pdf.read_bytes().startswith(b"%PDF-")
    assert 4 <= br.pdf_pages(pdf) <= 10


def test_the_pdf_is_the_one_its_stamp_describes() -> None:
    stamp = json.loads((ROOT / br.STAMP).read_text(encoding="utf-8"))
    pdf = (ROOT / br.PDF).read_bytes()
    assert stamp["pdf_sha256"] == hashlib.sha256(pdf).hexdigest()
    assert stamp["pages"] == br.pdf_pages(ROOT / br.PDF)
    assert stamp["pandoc"] == f"pandoc {br.PANDOC_VERSION}"


def test_the_pdf_was_built_from_the_current_sources() -> None:
    stamp = json.loads((ROOT / br.STAMP).read_text(encoding="utf-8"))
    assert stamp["sources_sha256"] == br.sources_sha256(ROOT), (
        "a README section, a doc or a result the report quotes changed after docs/REPORT.pdf "
        "was built; run make report-pdf"
    )
    assert br.stamp_problems(ROOT) == []


def test_the_pdf_is_tagged_with_its_language_and_an_outline() -> None:
    """A screen reader needs the tags and the language; the outline lets a reader jump to a part.

    Chromium writes an untagged PDF unless the print script asks for tags (hard rule 17).
    """
    pdf = (ROOT / br.PDF).read_bytes()
    assert b"/StructTreeRoot" in pdf, "docs/REPORT.pdf has no tags; print it with tagged: true"
    assert re.search(rb"/MarkInfo\s*<<[^>]*/Marked\s+true", pdf), "the PDF is not marked tagged"
    assert re.search(rb"/Lang\s*\(en\)", pdf), "the PDF does not say it is in English"
    assert b"/Outlines" in pdf, "docs/REPORT.pdf has no outline; print it with outline: true"


def test_the_readme_and_the_devpost_text_link_the_report() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    built = br.section_body(readme, "How this was built", "README.md")
    assert "docs/REPORT.pdf" in built
    devpost = (ROOT / "docs" / "devpost.md").read_text(encoding="utf-8")
    outside_blocks = re.sub(r"```.*?```", "", devpost, flags=re.S)
    assert "docs/REPORT.pdf" in outside_blocks, "link it outside the paste blocks"


def test_make_report_pdf_runs_the_build() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert re.search(r"^report-pdf:\n\t\$\(PY\) scripts/build_report\.py$", makefile, re.M)


# How it is assembled ---------------------------------------------------------------------------


def tree(tmp_path: Path, source: str, readme: str, result: dict[str, object]) -> Path:
    (tmp_path / "docs" / "report").mkdir(parents=True)
    (tmp_path / "results").mkdir()
    (tmp_path / "apps" / "web" / "scripts").mkdir(parents=True)
    (tmp_path / br.SOURCE).write_text(source, encoding="utf-8")
    (tmp_path / "README.md").write_text(readme, encoding="utf-8")
    (tmp_path / "results" / "r.json").write_text(json.dumps(result), encoding="utf-8")
    for rel in (br.TEMPLATE, br.STYLESHEET, br.PRINTER):
        (tmp_path / rel).write_text(f"{rel}\n", encoding="utf-8")
    return tmp_path


README = """Line one.

## Numbers

We kept <!--v:results/r.json#/kept-->35<!--/v--> flags.
<!-- claim: results/r.json#/real = True -->

### Inside

Not taken.

## Build

See [the write-up](WRITEUP.md) and [their brief](https://example.org/brief.pdf).
"""
SOURCE = """<!-- a note for editors, {{section:nowhere.md#Gone}} -->
## Abstract

Frames: {{claim:results/r.json#/frames}}.

{{section:README.md#Numbers}}

{{section:README.md#Build}}
"""
RESULT: dict[str, object] = {"kept": 35, "frames": 46, "real": True}


def test_a_section_is_its_text_up_to_the_next_heading_with_numbers_checked(tmp_path: Path) -> None:
    doc = br.assemble(tree(tmp_path, SOURCE, README, RESULT))
    assert "We kept 35 flags." in doc.markdown
    assert "Frames: 46." in doc.markdown
    assert "Not taken" not in doc.markdown and "Inside" not in doc.markdown
    assert "<!--" not in doc.markdown and "{{" not in doc.markdown
    assert doc.inputs == {"docs/report/source.md", "README.md", "results/r.json"}


def test_a_link_to_a_file_here_becomes_a_link_to_the_repository(tmp_path: Path) -> None:
    doc = br.assemble(tree(tmp_path, SOURCE, README, RESULT))
    assert f"[the write-up]({br.REPO_URL}WRITEUP.md)" in doc.markdown
    assert "[their brief](https://example.org/brief.pdf)" in doc.markdown


def test_a_number_the_readme_shows_that_drifted_from_results_refuses(tmp_path: Path) -> None:
    root = tree(tmp_path, SOURCE, README, {**RESULT, "kept": 36})
    with pytest.raises(br.ReportError, match="shows 35 .* says 36"):
        br.assemble(root)


def test_a_claim_marker_that_drifted_refuses(tmp_path: Path) -> None:
    root = tree(tmp_path, SOURCE, README, {**RESULT, "real": False})
    with pytest.raises(br.ReportError, match="drifted"):
        br.assemble(root)


def test_a_missing_or_doubled_heading_refuses(tmp_path: Path) -> None:
    root = tree(tmp_path, SOURCE.replace("#Build", "#Built"), README, RESULT)
    with pytest.raises(br.ReportError, match="no heading called 'Built'"):
        br.assemble(root)
    with pytest.raises(br.ReportError, match="2 headings"):
        br.section_body("## A\none\n## A\ntwo\n", "A")


def test_a_heading_inside_a_code_fence_is_not_a_heading() -> None:
    text = "## Real\nbefore\n```\n## Not a heading\n```\nafter\n## Next\n"
    assert br.section_body(text, "Real") == "before\n```\n## Not a heading\n```\nafter"


def test_a_token_left_over_or_a_dash_refuses(tmp_path: Path) -> None:
    root = tree(tmp_path, SOURCE + "\n{{claim:results/r.json#/missing}}\n", README, RESULT)
    with pytest.raises(br.ReportError, match="cannot be read"):
        br.assemble(root)
    dash = chr(0x2014)
    root2 = tree(tmp_path / "b", SOURCE + f"\nA dash {dash} here.\n", README, RESULT)
    with pytest.raises(br.ReportError, match="em or en dash"):
        br.assemble(root2)


def test_the_sources_hash_changes_with_the_text_the_look_and_the_printer(tmp_path: Path) -> None:
    root = tree(tmp_path, SOURCE, README, RESULT)
    before = br.sources_sha256(root)
    for rel in (br.TEMPLATE, br.STYLESHEET, br.PRINTER):
        path = root / rel
        path.write_text(path.read_text(encoding="utf-8") + "x", encoding="utf-8")
        after = br.sources_sha256(root)
        assert after != before, rel
        before = after
    (root / "results" / "r.json").write_text(json.dumps({**RESULT, "frames": 47}))
    assert br.sources_sha256(root) != before


def test_the_stamp_problems_name_a_stale_pdf_and_a_wrong_page_count(tmp_path: Path) -> None:
    root = tree(tmp_path, SOURCE, README, RESULT)
    (root / "docs").mkdir(exist_ok=True)
    assert br.stamp_problems(root) == ["docs/REPORT.pdf does not exist; run make report-pdf"]
    shutil.copy(ROOT / br.PDF, root / br.PDF)
    pages = br.pdf_pages(root / br.PDF)
    stamp = {
        "pages": pages,
        "pdf_sha256": hashlib.sha256((root / br.PDF).read_bytes()).hexdigest(),
        "sources_sha256": br.sources_sha256(root),
    }
    (root / br.STAMP).write_text(json.dumps(stamp), encoding="utf-8")
    assert br.stamp_problems(root) == []
    (root / "results" / "r.json").write_text(json.dumps({**RESULT, "frames": 47}))
    assert any("older sources" in p for p in br.stamp_problems(root))
    (root / br.STAMP).write_text(json.dumps({**stamp, "pages": pages + 1}), encoding="utf-8")
    assert any("the stamp says" in p for p in br.stamp_problems(root))


def test_pages_are_counted_from_page_objects_not_the_page_tree(tmp_path: Path) -> None:
    path = tmp_path / "x.pdf"
    path.write_bytes(b"%PDF-1.4\n<< /Type /Pages /Count 2 >>\n<< /Type /Page >>\n<</Type/Page>>\n")
    assert br.pdf_pages(path) == 2
