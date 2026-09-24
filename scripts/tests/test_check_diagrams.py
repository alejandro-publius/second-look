"""The diagrams gate: labelled edges, SVGs drawn from their sources, copies that match, and the
renderer pinned and wired into make check and CI (UPDATE_27 block 23)."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest
import yaml

from scripts import check_diagrams

REPO = Path(__file__).resolve().parents[2]
TOOL = REPO / "tools" / "diagrams"
NAMES = ("system-map", "fhir-graph", "ai-gate")


def _copy_diagrams(tmp_path: Path) -> Path:
    shutil.copytree(REPO / "docs" / "diagrams", tmp_path / "docs" / "diagrams")
    return tmp_path


def test_the_repository_passes() -> None:
    assert check_diagrams.main(root=REPO) == 0


def test_the_three_diagrams_are_there_with_their_svgs() -> None:
    folder = REPO / "docs" / "diagrams"
    assert sorted(p.stem for p in folder.glob("*.mmd")) == sorted(NAMES)
    for name in NAMES:
        assert (folder / f"{name}.svg").read_text(encoding="utf-8").startswith("<!-- Drawn by")


def test_an_edge_needs_a_label() -> None:
    head = "flowchart TB\n  A[a]\n  B[b]\n"
    assert check_diagrams.unlabelled_edges(head + '  A -- "water" --> B\n') == []
    assert check_diagrams.unlabelled_edges(head + "  A -->|water| B\n") == []
    assert check_diagrams.unlabelled_edges(head + '  A -. "maybe" .-> B\n') == []
    assert check_diagrams.unlabelled_edges(head + '  A <-- "both ways" --> B\n') == []
    assert check_diagrams.unlabelled_edges(head + '  A -- "ends in a circle" --o B\n') == []
    assert check_diagrams.unlabelled_edges(head + "  A --x|ends in a cross| B\n") == []
    for bare in (
        "  A --> B\n",
        '  A -- "" --> B\n',
        "  A ~~~ B\n",
        '  A -- "x" --> B --> A\n',
        "  A --o B\n",
        "  A --x B\n",
        "  A o--o B\n",
        "  A x--x B\n",
        "  A ==o B\n",
    ):
        problems = check_diagrams.unlabelled_edges(head + bare)
        assert len(problems) == 1 and problems[0].startswith("line 4:"), bare


def test_edge_labels_are_only_asked_of_flowcharts() -> None:
    assert check_diagrams.unlabelled_edges("sequenceDiagram\n  A->>B: hi\n") == []


def test_sequence_blocks_close_with_end() -> None:
    ok = "sequenceDiagram\n  alt yes\n    A->>B: x\n  else no\n    B->>A: y\n  end\n"
    assert check_diagrams.check_source(ok) == []
    assert any("never closed" in p for p in check_diagrams.check_source(ok.replace("  end\n", "")))
    assert any("no alt" in p for p in check_diagrams.check_source(ok + "  end\n"))
    flow = 'flowchart TB\n  subgraph S["s"]\n    A[a]\n  end\n  end\n'
    assert any("no subgraph" in p for p in check_diagrams.check_source(flow))


def test_a_source_edited_after_its_render_fails(tmp_path: Path) -> None:
    root = _copy_diagrams(tmp_path)
    src = root / "docs" / "diagrams" / "system-map.mmd"
    src.write_text(src.read_text(encoding="utf-8").replace("Open-Meteo", "Open Meteo"))
    problems = check_diagrams.source_problems(root)
    assert problems == [
        "docs/diagrams/system-map.svg: drawn from another version of system-map.mmd; "
        "run make diagrams-render"
    ]


def test_an_svg_edited_by_hand_fails(tmp_path: Path) -> None:
    """Even an edit that only moves a label: the stamp holds the sha256 of the drawing."""
    root = _copy_diagrams(tmp_path)
    svg = root / "docs" / "diagrams" / "system-map.svg"
    text = svg.read_text(encoding="utf-8")
    # Whatever offset this machine's fonts gave the first label, move it by a few pixels.
    offset = re.search(r'<text y="(-?[0-9.]+)"', text)
    assert offset is not None
    moved = f"{float(offset.group(1)) - 2.3:.1f}"
    svg.write_text(text.replace(offset.group(0), f'<text y="{moved}"', 1))
    assert check_diagrams.source_problems(root) == [
        "docs/diagrams/system-map.svg: edited by hand after it was drawn; run make diagrams-render"
    ]


def _rows(*rows: tuple[str, ...]) -> str:
    """Label rows as Mermaid draws them in a flowchart SVG: one tspan per word inside a row."""
    return "".join(
        '<tspan class="text-outer-tspan row" x="0" y="1em" dy="1.1em">'
        + "".join(f'<tspan class="text-inner-tspan">{word}</tspan>' for word in row)
        + "</tspan>"
        for row in rows
    )


def test_a_label_that_wraps_on_its_own_fails() -> None:
    """Mermaid breaks an edge label wider than 200 pixels where this machine's fonts say."""
    source = (
        'flowchart TB\n  A["a node"]\n  B["rain & wind"]\n  A -- "short<br/>then a line" --> B\n'
    )
    nodes = (("a", " node"), ("rain", " &amp;", " wind"))
    drawn = _rows(*nodes, ("short",), ("then", " a", " line"))
    assert check_diagrams.wrapped_rows(source, drawn) == []
    wrapped = _rows(*nodes, ("short",), ("then", " a"), ("line",))
    assert check_diagrams.wrapped_rows(source, wrapped) == [
        "a label wrapped on its own at 'then a'",
        "a label wrapped on its own at 'line'",
    ]
    assert check_diagrams.wrapped_rows(source, "<svg></svg>") == [
        "no label rows found in the SVG, so the wrap check cannot read it"
    ]
    assert check_diagrams.wrapped_rows("sequenceDiagram\n  A->>B: hi\n", wrapped) == []


def test_a_drawing_whose_rows_are_not_the_source_lines_fails(tmp_path: Path) -> None:
    """The wrap check runs on the real SVGs: here the rows no longer match the source's lines."""
    root = _copy_diagrams(tmp_path)
    folder = root / "docs" / "diagrams"
    src = folder / "system-map.mmd"
    old = src.read_text(encoding="utf-8")
    new = old.replace(
        '"one lab Observation<br/>of theirs, read once<br/>a day from the Mac"',
        '"one lab Observation of theirs,<br/>read once a day from the Mac"',
    )
    assert new != old
    src.write_text(new, encoding="utf-8")
    svg = folder / "system-map.svg"
    stamp_old = check_diagrams._sha256(old.encode("utf-8"))
    stamp_new = check_diagrams._sha256(new.encode("utf-8"))
    svg.write_text(svg.read_text(encoding="utf-8").replace(stamp_old, stamp_new, 1), "utf-8")
    problems = check_diagrams.source_problems(root)
    assert len(problems) == 3 and all("a label wrapped on its own" in p for p in problems)


def test_a_missing_svg_an_orphan_svg_and_a_missing_stamp_fail(tmp_path: Path) -> None:
    root = _copy_diagrams(tmp_path)
    folder = root / "docs" / "diagrams"
    (folder / "ai-gate.svg").unlink()
    (folder / "extra.svg").write_text("<svg/>\n")
    fhir = folder / "fhir-graph.svg"
    fhir.write_text(fhir.read_text(encoding="utf-8").split("\n", 1)[1])
    problems = "\n".join(check_diagrams.source_problems(root))
    assert "ai-gate.mmd: no SVG next to it" in problems
    assert "extra.svg: an SVG with no .mmd source" in problems
    assert "fhir-graph.svg: no stamp naming fhir-graph.mmd" in problems


def test_a_source_names_itself_for_a_screen_reader(tmp_path: Path) -> None:
    root = _copy_diagrams(tmp_path)
    src = root / "docs" / "diagrams" / "ai-gate.mmd"
    text = src.read_text(encoding="utf-8")
    src.write_text(re.sub(r"^\s*acc(Title|Descr):.*\n", "", text, flags=re.M))
    problems = "\n".join(check_diagrams.source_problems(root))
    assert "ai-gate.mmd: no accTitle" in problems and "ai-gate.mmd: no accDescr" in problems


def test_an_unlabelled_edge_in_a_source_fails(tmp_path: Path) -> None:
    root = _copy_diagrams(tmp_path)
    src = root / "docs" / "diagrams" / "system-map.mmd"
    src.write_text(src.read_text(encoding="utf-8") + "  MCP --> CLIENT\n")
    problems = "\n".join(check_diagrams.source_problems(root))
    assert "system-map.mmd: line" in problems and "an edge with no label" in problems


def test_a_copy_in_markdown_must_match_its_source(tmp_path: Path) -> None:
    root = _copy_diagrams(tmp_path)
    source = (root / "docs" / "diagrams" / "fhir-graph.mmd").read_text(encoding="utf-8")
    same = [("docs/x.md:3", source.rstrip("\n"))]
    assert check_diagrams.copy_problems(root, same) == []
    drifted = [("docs/x.md:3", source.replace("partOf", "part of", 1))]
    assert check_diagrams.copy_problems(root, drifted) == [
        "docs/x.md:3: a copy of docs/diagrams/fhir-graph.mmd that differs from it; "
        "paste the source again"
    ]
    other = [("docs/x.md:3", "flowchart TB\n  A -- x --> B")]
    assert check_diagrams.copy_problems(root, other) == []


def test_architecture_carries_the_three_sources_word_for_word() -> None:
    blocks = [source for _, source in check_diagrams.blocks_in(REPO / "docs" / "ARCHITECTURE.md")]
    for name in NAMES:
        text = (REPO / "docs" / "diagrams" / f"{name}.mmd").read_text(encoding="utf-8")
        assert text.rstrip("\n") in blocks, name


def _web_playwright_version() -> str:
    lock = json.loads((REPO / "apps" / "web" / "package-lock.json").read_text(encoding="utf-8"))
    return str(lock["packages"]["node_modules/playwright-core"]["version"])


def test_the_renderer_is_pinned_and_finds_the_chromium_apps_web_installs() -> None:
    pkg = json.loads((TOOL / "package.json").read_text(encoding="utf-8"))
    deps = pkg["devDependencies"]
    assert set(deps) == {"@mermaid-js/mermaid-cli", "playwright-core", "puppeteer"}
    for name, version in deps.items():
        assert re.fullmatch(r"\d+\.\d+\.\d+", version), f"{name} is not pinned: {version}"
    # playwright-core finds the browser by its own version, so it must be apps/web's, or the
    # renderer looks for a Chromium that `npx playwright install chromium` never put there.
    assert deps["playwright-core"] == _web_playwright_version()
    lock = json.loads((TOOL / "package-lock.json").read_text(encoding="utf-8"))
    for name, version in deps.items():
        assert lock["packages"][f"node_modules/{name}"]["version"] == version
    assert "skipDownload: true" in (TOOL / ".puppeteerrc.cjs").read_text(encoding="utf-8")


def test_make_check_and_ci_run_the_render_check() -> None:
    make = (REPO / "Makefile").read_text(encoding="utf-8")
    check_line = next(ln for ln in make.splitlines() if ln.startswith("check:") and "lint" in ln)
    assert " diagrams " in f"{check_line} "
    target = make.split("\ndiagrams:\n", 1)[1].split("\n\n", 1)[0]
    assert "scripts/check_diagrams.py" in target
    assert "node --test" in target and "node render.mjs --check" in target
    workflow = (REPO / ".github" / "workflows" / "check.yml").read_text(encoding="utf-8")
    steps = workflow.split("\n      - ")
    install = next(i for i, s in enumerate(steps) if "cd tools/diagrams && npm ci" in s)
    browser = next(i for i, s in enumerate(steps) if "npx playwright install" in s)
    run_check = next(i for i, s in enumerate(steps) if s.split("\n", 1)[0] == "run: make check")
    assert browser < run_check and install < run_check
    assert "tools/diagrams/package-lock.json" in workflow


@pytest.mark.parametrize("name", NAMES)
def test_no_svg_gives_a_test_answer_away(name: str) -> None:
    """Hard rule 17: nothing in a diagram or its alt text names a test item or its answer."""
    text = (REPO / "docs" / "diagrams" / f"{name}.mmd").read_text(encoding="utf-8")
    doc = yaml.safe_load((REPO / "content" / "test_items.yaml").read_text(encoding="utf-8"))
    rows = doc["items"] + doc.get("warmup", [])
    ids = {str(r["id"]) for r in rows} | {str(r["photo_id"]) for r in rows}
    assert len(ids) > 16, "the test items and their photos"
    assert not [i for i in ids if re.search(rf"\b{re.escape(i)}\b", text)]
