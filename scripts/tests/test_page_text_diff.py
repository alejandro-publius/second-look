"""scripts/page_text_diff.py: markup may change, a string a person sees or hears may not."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import page_text_diff

BEFORE = """<!DOCTYPE html><html><head><title>Second Look</title>
<meta name="description" content="Two minutes on creek damage."/>
<link rel="preload" href="/photos/a.jpg" as="image"/>
<script>self.push("some payload")</script><style>.photo{width:1px}</style></head>
<body><h1>Which creek is healthier?</h1>
<div role="group" aria-label="Two creek photos">
<img class="photo" src="/photos/a.jpg" alt="photo of a creek" width="1600" height="1080"/>
</div><button>Pick this one</button></body></html>"""

# The same page with the photo in a <picture>, an AVIF preload, and a different payload script.
AFTER = (
    BEFORE.replace(
        '<link rel="preload" href="/photos/a.jpg" as="image"/>',
        '<link rel="preload" as="image" type="image/avif" imageSrcSet="/photos/a-480.avif 480w"/>',
    )
    .replace(
        '<img class="photo"',
        '<picture><source type="image/avif" srcSet="/photos/a-480.avif 480w"/><img class="photo"',
    )
    .replace('height="1080"/>', 'height="1080"/></picture>')
    .replace("some payload", "another payload")
)


def export(root: Path, pages: dict[str, str]) -> Path:
    for rel, html in pages.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(html, encoding="utf-8")
    return root


def run(
    tmp_path: Path, after: dict[str, str], capsys: pytest.CaptureFixture[str]
) -> tuple[int, str]:
    before = export(tmp_path / "before", {"index.html": BEFORE, "t.html": BEFORE})
    code = page_text_diff.main([str(before), str(export(tmp_path / "after", after))])
    return code, capsys.readouterr().out


def test_the_strings_include_text_alt_labels_and_the_description() -> None:
    words = page_text_diff.page_words(BEFORE)
    assert "Second Look" in words
    assert "[meta description] Two minutes on creek damage." in words
    assert "[div aria-label] Two creek photos" in words
    assert "[img alt] photo of a creek" in words
    assert "Pick this one" in words
    assert not [w for w in words if "payload" in w or "width:1px" in w]


def test_markup_only_changes_give_an_empty_diff(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert AFTER != BEFORE
    code, out = run(tmp_path, {"index.html": AFTER, "t.html": BEFORE}, capsys)
    assert code == 0
    assert out == "page-text-diff: 2 pages, the same strings on every one\n"


@pytest.mark.parametrize(
    ("old", "new", "line"),
    [
        ("Pick this one", "Choose this one", "+Choose this one"),
        ('alt="photo of a creek"', 'alt="a clean creek"', "+[img alt] a clean creek"),
        ('aria-label="Two creek photos"', 'aria-label="Photos"', "+[div aria-label] Photos"),
        ("on creek damage.", "on creeks.", "+[meta description] Two minutes on creeks."),
        ("<title>Second Look</title>", "<title>Look</title>", "+Look"),
    ],
)
def test_a_changed_string_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], old: str, new: str, line: str
) -> None:
    changed = AFTER.replace(old, new)
    assert changed != AFTER
    code, out = run(tmp_path, {"index.html": BEFORE, "t.html": changed}, capsys)
    assert code == 1
    assert "--- before/t.html" in out
    assert line in out.splitlines()


def test_a_page_only_one_export_has_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out = run(tmp_path, {"index.html": BEFORE}, capsys)
    assert code == 1
    assert "only in before: t.html" in out


def test_a_folder_without_an_export_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    before = export(tmp_path / "before", {"index.html": BEFORE})
    (tmp_path / "empty").mkdir()
    assert page_text_diff.main([str(before), str(tmp_path / "empty")]) == 1
    assert "no static export" in capsys.readouterr().out
