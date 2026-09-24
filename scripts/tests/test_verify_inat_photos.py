"""What the credits page says about the iNaturalist photos comes from iNaturalist's own answer:
research grade, inside California, and the author and licence the manifest names."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts import verify_inat_photos as v

ROOT = Path(__file__).resolve().parents[2]
ROW = {
    "id": "ph-plant-05",
    "role": "lesson",
    "source_url": "https://www.inaturalist.org/observations/172266217",
    "author": "Pinnacles National Park",
    "license": "CC-BY-4.0",
}


def observation(**over: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "quality_grade": "research",
        "place_ids": [1, 14, 1527],
        "place_guess": "San Benito County, CA, USA",
        "taxon": {"name": "Rubus armeniacus"},
        "user": {"login": "pinn", "name": "Pinnacles National Park"},
        "photos": [
            {
                "license_code": "cc-by",
                "attribution": "(c) Pinnacles National Park, some rights reserved (CC BY)",
            }
        ],
    }
    base.update(over)
    return base


def test_a_research_grade_california_observation_with_the_right_credit() -> None:
    got = v.verdict(ROW, observation())
    assert got["research_grade"] and got["in_california"] and got["author_and_licence_match"]
    assert got["observation_id"] == 172266217


def test_not_research_grade_is_said() -> None:
    assert v.verdict(ROW, observation(quality_grade="needs_id"))["research_grade"] is False


def test_outside_california_is_said() -> None:
    assert v.verdict(ROW, observation(place_ids=[1, 18]))["in_california"] is False


def test_a_different_author_or_licence_is_said() -> None:
    other = [{"license_code": "cc-by", "attribution": "(c) Someone Else, some rights reserved"}]
    assert v.verdict(ROW, observation(photos=other))["author_and_licence_match"] is False
    nc = [{"license_code": "cc-by-nc", "attribution": "(c) Pinnacles National Park"}]
    assert v.verdict(ROW, observation(photos=nc))["author_and_licence_match"] is False


def test_a_missing_observation_is_nothing_true() -> None:
    got = v.verdict(ROW, None)
    assert got["found"] is False
    assert not (got["research_grade"] or got["in_california"] or got["author_and_licence_match"])


def test_every_inaturalist_photo_in_the_manifest_has_an_answer() -> None:
    assert v.check() == []


def test_the_check_notices_a_photo_with_no_answer(tmp_path: Path) -> None:
    doc = json.loads(v.RESULTS.read_text(encoding="utf-8"))
    doc["photos"] = doc["photos"][1:]
    stale = tmp_path / "inat_photos.json"
    stale.write_text(json.dumps(doc), encoding="utf-8")
    problems = v.check(stale)
    assert len(problems) == 1 and "has no iNaturalist answer" in problems[0]


def test_the_committed_answers_say_what_the_credits_page_says() -> None:
    """The credits page calls a photo research grade and Californian only on these answers."""
    doc = json.loads(v.RESULTS.read_text(encoding="utf-8"))
    s = doc["summary"]
    assert s["photos"] == len(doc["photos"]) == len(v.inat_rows())
    assert s["research_grade_in_california"] == sum(
        1 for p in doc["photos"] if p["research_grade"] and p["in_california"]
    )
