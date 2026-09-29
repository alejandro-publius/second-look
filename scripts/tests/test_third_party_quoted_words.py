"""docs/THIRD_PARTY.md names the official app's wording, which we quote and do not own."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import third_party

REPO = Path(__file__).resolve().parents[2]
HEADING = "## Words we quote"
NOT_OURS = "they are not under our MIT or CC BY 4.0 licences"


def app_strings(root: Path, languages: list[str], fallback: dict[str, dict[str, str]]) -> Path:
    (root / "content").mkdir(parents=True)
    doc = {
        "source": {
            "app": "The Pond App",
            "app_url": "https://pond.example/",
            "bundle_sha256": "ab" * 32,
            "fetched": "2026-01-02",
        },
        "languages": languages,
        "fallback": fallback,
    }
    (root / "content" / "app_strings.json").write_text(json.dumps(doc), encoding="utf-8")
    return root


def section(text: str) -> str:
    _, found, rest = text.partition(f"\n{HEADING}\n")
    assert found, f"no section {HEADING!r}"
    return rest.split("\n## ", 1)[0].strip()


def test_every_fact_in_the_entry_is_read_from_the_app_strings_file(tmp_path: Path) -> None:
    root = app_strings(tmp_path, ["en", "fr"], {"fr": {"a.text": "differs", "b.text": "differs"}})
    entry = third_party.quoted_words(root)
    assert entry.startswith(f"{HEADING}\n\n- The Pond App (https://pond.example): ")
    assert "in 2 of its languages (English and French)" in entry
    assert "translation file on 2026-01-02" in entry
    assert f"(`{'ab' * 32}`)" in entry
    assert "differs from the English (2 strings)" in entry
    assert NOT_OURS in entry


def test_a_language_with_no_name_stops_the_build(tmp_path: Path) -> None:
    root = app_strings(tmp_path, ["en", "xx"], {})
    with pytest.raises(ValueError, match="no name for the language xx"):
        third_party.quoted_words(root)


def test_the_list_says_the_apps_words_are_not_under_our_licences() -> None:
    source = json.loads((REPO / "content" / "app_strings.json").read_text(encoding="utf-8"))
    text = third_party.build(REPO)
    entry = section(text)
    assert source["source"]["app"] in entry
    assert source["source"]["bundle_sha256"] in entry
    assert f"in {len(source['languages'])} of its languages" in entry
    assert "The words belong to the OneAquaHealth project." in entry
    assert NOT_OURS in entry
    assert text.index("## External services") < text.index(HEADING) < text.index("## Design ref")
    assert "under neither licence" in text.split("\n")[2]


def test_the_committed_list_has_the_entry_the_script_writes() -> None:
    committed = (REPO / "docs" / "THIRD_PARTY.md").read_text(encoding="utf-8")
    assert section(committed) == section(third_party.build(REPO)), (
        "run: uv run python scripts/third_party.py"
    )


def test_every_path_the_entry_names_is_in_the_repository() -> None:
    entry = third_party.quoted_words(REPO)
    for path in (
        "content/app_strings.json",
        "scripts/app_strings.py",
        "docs/notes/app_translations.md",
        "docs/notes/app_strings.md",
    ):
        assert path in entry
        assert (REPO / path).is_file(), path
