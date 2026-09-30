"""make new-city: four files, no claims, a valid pack, nested Locations, and no silent overwrite."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from core.regions import creeks_from_regions
from scripts import new_city


@pytest.fixture
def root(tmp_path: Path) -> Path:
    locales = tmp_path / "content" / "locales"
    locales.mkdir(parents=True)
    (locales / "en.json").write_text(
        json.dumps(
            {
                "landing.hook": "Which creek is healthier?",
                "time.test": "about four minutes",
                "poster.scan": "Scan. It takes {time.test}.",
            }
        )
    )
    return tmp_path


def test_scaffold_writes_the_four_files_and_the_time(root: Path, monkeypatch) -> None:
    monkeypatch.setattr(new_city, "qr_svg", lambda url: "<svg>qr</svg>")
    written = new_city.scaffold(
        root=root, name="Heraklion", country="Greece", lat=35.3387, lon=25.1442
    )
    rel = [str(p.relative_to(root)) for p in written]
    assert rel == [
        "content/regions/heraklion.yaml",
        "fhir/fsh/city-heraklion.fsh",
        "docs/cities/heraklion/poster.html",
        "docs/cities/heraklion/CHECKLIST.md",
        "docs/cities/TIMES.md",
    ]
    times = (root / "docs" / "cities" / "TIMES.md").read_text()
    assert "| Heraklion | `scripts/new_city.py` |" in times and "seconds, 4 files" in times


def test_the_region_pack_stub_loads_and_holds_no_claim(root: Path, monkeypatch) -> None:
    monkeypatch.setattr(new_city, "qr_svg", lambda url: None)
    new_city.scaffold(root=root, name="Heraklion", country="Greece", lat=35.3387, lon=25.1442)
    pack = yaml.safe_load((root / "content" / "regions" / "heraklion.yaml").read_text())
    assert pack["region"] == "heraklion" and pack["name"] == "Heraklion, Greece"
    assert pack["approved"] is False and pack["invasive_plants"] == [] and pack["creeks"] == []
    assert creeks_from_regions({"heraklion": pack}) == []
    assert "local checker" in pack["source"]


def test_the_fsh_nests_city_creek_reach_and_spot_under_their_profile(
    root: Path, monkeypatch
) -> None:
    monkeypatch.setattr(new_city, "qr_svg", lambda url: None)
    new_city.scaffold(root=root, name="Heraklion", country="Greece", lat=35.3387, lon=25.1442)
    fsh = (root / "fhir" / "fsh" / "city-heraklion.fsh").read_text()
    assert fsh.count("InstanceOf: LocationOah") == 4
    assert "InstanceOf: Bundle" in fsh and "Usage: #example" in fsh
    assert '* type = $sct#288520005 "City environment"' in fsh, "their own type for a city"
    assert "* position.latitude = 35.3387" in fsh and "* position.longitude = 25.1442" in fsh
    assert "* partOf = Reference(Location/sl-city-heraklion)" in fsh
    assert "* partOf = Reference(Location/sl-city-heraklion-creek-1)" in fsh
    assert "* partOf = Reference(Location/sl-city-heraklion-creek-1-reach-1)" in fsh
    assert "to be named" in fsh and "not a record" in fsh


def test_the_checklist_has_five_steps_and_says_no_claims(root: Path, monkeypatch) -> None:
    monkeypatch.setattr(new_city, "qr_svg", lambda url: None)
    new_city.scaffold(root=root, name="Heraklion", country="Greece", lat=35.3387, lon=25.1442)
    text = (root / "docs" / "cities" / "heraklion" / "CHECKLIST.md").read_text()
    steps = [line for line in text.splitlines() if line.startswith("## ") and line[3].isdigit()]
    assert [s[:4] for s in steps] == ["## 1", "## 2", "## 3", "## 4", "## 5"]
    assert "No claims." in text and "Nobody has run Second Look in Heraklion" in text
    assert "content/regions/heraklion.yaml" in text and "fhir/fsh/city-heraklion.fsh" in text
    assert "scripts/repush_sandbox.py --library" in text


def test_the_poster_uses_our_words_the_city_name_and_leaves_photo_slots_empty(
    root: Path, monkeypatch
) -> None:
    monkeypatch.setattr(
        new_city, "qr_svg", lambda url: "<svg>qr</svg>" if "src=poster" in url else None
    )
    new_city.scaffold(
        root=root,
        name="Heraklion",
        country="Greece",
        lat=35.3387,
        lon=25.1442,
        site="https://x.test/",
    )
    html = (root / "docs" / "cities" / "heraklion" / "poster.html").read_text()
    assert "<h1>Heraklion: Which creek is healthier?</h1>" in html
    # The poster quotes the test's time from time.test, as the web build does (judge walk W09).
    assert "Scan. It takes about four minutes." in html and "https://x.test/?src=poster" in html
    assert "{time." not in html
    assert "<svg>qr</svg>" in html
    assert html.count("goes here") == 2, "two empty slots, no borrowed photo"
    assert "photos/" not in html


def test_a_city_that_exists_is_not_overwritten_without_force(root: Path, monkeypatch) -> None:
    monkeypatch.setattr(new_city, "qr_svg", lambda url: None)
    new_city.scaffold(root=root, name="Heraklion", country="Greece", lat=35.3387, lon=25.1442)
    with pytest.raises(new_city.CityExists, match="use --force"):
        new_city.scaffold(root=root, name="Heraklion", country="Greece", lat=35.3387, lon=25.1442)
    assert (
        new_city.main(
            ["--name", "Heraklion", "--lat", "35.3", "--lon", "25.1", "--root", str(root)]
        )
        == 2
    )
    again = new_city.scaffold(
        root=root, name="Heraklion", country="Greece", lat=35.3387, lon=25.1442, force=True
    )
    assert len(again) == 5


def test_bad_coordinates_and_an_empty_name_are_refused(root: Path) -> None:
    with pytest.raises(ValueError, match="within 90"):
        new_city.scaffold(root=root, name="Nowhere", country="", lat=95.0, lon=0.0)
    assert new_city.main(["--name", "...", "--lat", "1", "--lon", "1", "--root", str(root)]) == 2


def test_the_pack_has_a_top_level_bbox_that_is_null_until_a_checker_sets_it(
    root: Path, monkeypatch
) -> None:
    """apps/web/lib/content.ts regionAt reads the pack's top level bbox to decide which plant
    list a pin is offered. The stub must carry the key, as null, and no made up box."""
    monkeypatch.setattr(new_city, "qr_svg", lambda url: None)
    new_city.scaffold(root=root, name="Heraklion", country="Greece", lat=35.3387, lon=25.1442)
    path = root / "content" / "regions" / "heraklion.yaml"
    pack = yaml.safe_load(path.read_text())
    assert "bbox" in pack and pack["bbox"] is None
    text = path.read_text()
    assert "[south, west, north, east]" in text and "[0, 1, 2, 3]" not in text, "no fake box"
    assert "offered only to a pin inside this box" in text
