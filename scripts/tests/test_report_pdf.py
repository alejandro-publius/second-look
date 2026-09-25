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
import zlib
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


def test_a_figure_is_the_committed_drawing_itself_with_its_caption(tmp_path: Path) -> None:
    svg = tmp_path / "docs" / "diagrams" / "x.svg"
    svg.parent.mkdir(parents=True)
    svg.write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")
    inputs: set[str] = set()
    md = br.figure(tmp_path, "docs/diagrams/x.svg", "A caption", inputs)
    assert md.startswith("![A caption](data:image/svg+xml;base64,")
    assert "*Figure: A caption.*" in md
    assert inputs == {"docs/diagrams/x.svg"}, "a changed drawing must make the report stale"
    with pytest.raises(br.ReportError):
        br.figure(tmp_path, "docs/diagrams/missing.svg", "x", inputs)


def test_code_breaks_only_after_a_slash_or_before_a_test_name() -> None:
    html = br.breakable_code("<p><code>core/fhir_emit.py</code> and a/b</p>")
    assert html == "<p><code>core/<wbr>fhir_emit.py</code> and a/b</p>"
    test = br.breakable_code("<code>core/tests/test_gate.py::test_a_long_name</code>")
    assert test == "<code>core/<wbr>tests/<wbr>test_gate.py::<wbr>test_a_long_name</code>"


def fake_pdf(scale: str, pages: int = 2) -> bytes:
    """Pages shaped as Chromium writes them: the page's transform, then the body's."""
    body = f".23999999 0 0 -.23999999 0 842.88 cm\nq\n{scale} 0 0 {scale} 187.5 175 cm\n"
    content = zlib.compress((body + "BT /F1 10 Tf (x) Tj ET\n").encode("ascii"))
    return b"%PDF-1.4\n" + (b"<< /Type /Page >>\nstream\n" + content + b"\nendstream\n") * pages


def test_a_report_chromium_shrank_to_fit_the_page_is_refused() -> None:
    """A table of test names wider than the page made Chromium print every page at 87%, so the
    body text fell from 9.4 to 8.2 pt with no error anywhere (critic round 09, while fixing L05)."""
    assert br.page_scales(fake_pdf("3.125")) == pytest.approx([0.75, 0.75])
    assert br.shrunk(fake_pdf("3.125"), 2) is None
    assert "shrank the pages to 87%" in (br.shrunk(fake_pdf("2.7166803"), 2) or "")
    assert "found on 2 of 3 pages" in (br.shrunk(fake_pdf("3.125"), 3) or "")


def test_the_committed_pdf_prints_at_full_size() -> None:
    pdf = ROOT / br.PDF
    assert br.shrunk(pdf.read_bytes(), br.pdf_pages(pdf)) is None


def test_a_folded_readme_table_is_printed_open() -> None:
    folded = (
        "Text.\n\n<details>\n<summary>Every risk</summary>\n\n| a | b |\n|---|---|\n\n</details>\n"
    )
    out = br.unfolded(folded)
    assert "<details>" not in out and "</details>" not in out and "<summary>" not in out
    assert "*Every risk*" in out and "| a | b |" in out
    # a blank line between the summary and the table, or pandoc prints the table as raw pipes
    assert re.search(r"\*Every risk\*\n[ \t]*\n\s*\| a \| b \|", out)
    # and with no blank line in the README, the report still gets one
    tight = br.unfolded("<summary>Every risk</summary>\n| a | b |\n")
    assert re.search(r"\*Every risk\*\n[ \t]*\n\s*\| a \| b \|", tight)


def test_a_table_left_as_pipe_text_stops_the_build() -> None:
    """CRITIC_07 J02: a table glued to the line above it printed as a paragraph of pipes."""
    glued = "<p><em>Every risk</em> | a | b | |---|---| | 1 | 2 |</p>"
    assert br.raw_tables(glued) == ["|---|"]
    assert br.raw_tables("<table><tr><td>a</td></tr></table>") == []
    assert br.raw_tables("<pre><code>| a |\n|---|</code></pre>") == []


# How big a figure prints (critic round 09 L04) ---------------------------------------------------


def svg(width: float, height: float, body: str, style: str = "", cap: str = "") -> str:
    """A drawing shaped the way the Mermaid CLI writes one; cap is its own max-width style."""
    return (
        f'<svg id="d" width="100%" xmlns="http://www.w3.org/2000/svg" '
        f'style="{cap}" viewBox="0 0 {width} {height}">'
        f"<style>#d{{font-family:arial;font-size:16px;}}{style}</style>{body}</svg>"
    )


def test_a_figure_too_wide_to_read_is_refused(tmp_path: Path) -> None:
    """The gate sequence, 2979.5 units wide, printed its labels at 2.7 pt and its step numbers at
    2.0 pt. A figure whose smallest text would print under 6 pt stops the build."""
    drawings = tmp_path / "docs" / "diagrams"
    drawings.mkdir(parents=True)
    wide = svg(3000, 1000, "<text>a label</text>", cap="max-width: 3000px;")
    (drawings / "wide.svg").write_text(wide, encoding="utf-8")
    with pytest.raises(br.ReportError, match=r"2\.7 pt, under 6 pt"):
        br.figure(tmp_path, "docs/diagrams/wide.svg", "Wide", set())
    (drawings / "narrow.svg").write_text(svg(600, 300, "<text>a label</text>"), encoding="utf-8")
    assert br.figure(tmp_path, "docs/diagrams/narrow.svg", "Narrow", set()).startswith("![Narrow]")
    # the two drawings the report once printed, as they are committed
    for rel in ("docs/diagrams/ai-gate.svg", "docs/diagrams/fhir-graph.svg"):
        with pytest.raises(br.ReportError, match="under 6 pt"):
            br.figure(ROOT, rel, "x", set())


def test_the_printed_text_size_counts_every_way_a_drawing_sets_one() -> None:
    # 600 units across the 504.6 pt text width: a unit prints at 0.84 pt
    scale = br.TEXT_WIDTH_PT / 600
    assert br.figure_text_pt(svg(600, 300, "<text>x</text>")) == pytest.approx(16 * scale)
    small = '<text>x</text><text font-size="8px">1</text>'
    assert br.figure_text_pt(svg(600, 300, small)) == pytest.approx(8 * scale)
    inline = '<text style="text-anchor: middle; font-size: 7px">x</text>'
    assert br.figure_text_pt(svg(600, 300, inline)) == pytest.approx(7 * scale)
    by_class = svg(600, 300, '<text class="tiny">x</text>', "#d .tiny{font-size:5px;}")
    assert br.figure_text_pt(by_class) == pytest.approx(5 * scale)
    # a style for something that is not text, such as Mermaid's tooltip, does not count
    tooltip = svg(600, 300, "<text>x</text>", "#d .mermaidTooltip{font-size:12px;}")
    assert br.figure_text_pt(tooltip) == pytest.approx(16 * scale)
    # a tall drawing is held to 5 inches high, so it prints narrower than the text width
    assert br.figure_text_pt(svg(600, 1200, "<text>x</text>")) == pytest.approx(16 * 180 / 600)
    # and a drawing that caps its own width in pixels prints no wider than that
    capped = svg(600, 300, "<text>x</text>", cap="max-width: 600px;")
    assert br.figure_text_pt(capped) == pytest.approx(16 * 600 * 0.75 / 600)
    # a drawing with no text has nothing to read; one with text and no viewBox cannot be judged
    assert br.figure_text_pt("<svg xmlns='http://www.w3.org/2000/svg'/>") is None
    with pytest.raises(br.ReportError, match="viewBox"):
        br.figure_text_pt("<svg><text>x</text></svg>")


def test_the_figure_check_uses_the_page_the_report_is_printed_on() -> None:
    printer = (ROOT / br.PRINTER).read_text(encoding="utf-8")
    assert 'format: "A4"' in printer
    assert 'left: "16mm", right: "16mm"' in printer
    assert br.TEXT_WIDTH_PT == pytest.approx((210 - 32) * 72 / 25.4)
    css = (ROOT / br.STYLESHEET).read_text(encoding="utf-8")
    img = re.search(r"^img \{(.*?)\}", css, re.S | re.M)
    assert img and "max-width: 100%;" in img.group(1) and "max-height: 5in;" in img.group(1)
    assert br.FIGURE_MAX_HEIGHT_PT == 5 * 72
