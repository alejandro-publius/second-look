"""The Library entry: golden file, their profile's must haves, and the checks broken on purpose."""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

import pytest

from core.fhir_emit import REPO_URL
from core.fhir_library import (
    EXT_RECORDS,
    EXT_SIZE,
    LIBRARY_URL,
    OAH_LIBRARY_PROFILE,
    check_library,
    library_entry,
)

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "fhir" / "golden" / "library-second-look.json"
TODAY = date(2026, 9, 21)


def normalise(resource: dict) -> str:
    return json.dumps(resource, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


@pytest.fixture
def library() -> dict:
    return library_entry(today=TODAY, n_records=1, provenance_refs=["Provenance/452"])


def test_library_matches_golden(library: dict) -> None:
    text = normalise(library)
    if os.environ.get("SL_UPDATE_GOLDEN") == "1":
        GOLDEN.write_text(text, encoding="utf-8")
    assert GOLDEN.exists(), "run with SL_UPDATE_GOLDEN=1 once to write the golden"
    assert text == GOLDEN.read_text(encoding="utf-8")
    assert check_library(json.loads(GOLDEN.read_text(encoding="utf-8"))) == []


def test_it_is_their_shape_and_points_at_our_repository(library: dict) -> None:
    assert library["meta"]["profile"] == [OAH_LIBRARY_PROFILE]
    assert library["url"] == LIBRARY_URL
    assert library["status"] == "active" and library["date"] == "2026-09-21"
    assert library["version"] == "2026.09"
    assert library["type"]["coding"][0]["code"] == "asset-collection"
    by_url = {e["url"]: e for e in library["extension"]}
    assert by_url[EXT_SIZE]["valueQuantity"] == {"value": 1, "unit": "visit records"}
    assert by_url[EXT_RECORDS]["valueInteger"] == 1
    urls = [c["url"] for c in library["content"]]
    assert urls[0] == REPO_URL, "the repository comes first: that is the FAIR pointer"
    assert urls[-1] == "Provenance/452", "and the mirrored record on the same server comes last"
    assert "1 visit record mirrored" in library["description"]
    assert "EXAMPLE" not in json.dumps(library), "the Library is a real entry, not an example"


def test_no_provenance_yet_is_still_a_valid_entry() -> None:
    empty = library_entry(today=TODAY, n_records=0)
    assert check_library(empty) == []
    assert all(not c["url"].startswith("Provenance/") for c in empty["content"])
    with pytest.raises(ValueError):
        library_entry(today=TODAY, n_records=-1)


def test_check_library_catches_a_broken_entry(library: dict) -> None:
    no_profile = {**library, "meta": {}}
    assert "not under their LibraryOah profile" in check_library(no_profile)
    no_repo = {**library, "content": library["content"][1:]}
    assert "does not point at the repository" in check_library(no_repo)
    no_ext = {**library, "extension": []}
    assert "missing the size or numberOfRecords extension" in check_library(no_ext)
    no_date = {**library, "date": ""}
    assert "missing date" in check_library(no_date)
    assert check_library({"resourceType": "Observation"}) == ["not a Library"]
