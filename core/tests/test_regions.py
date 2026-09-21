"""Creeks and reaches from the region pack, and where a spot sits on them."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from core.records import Spot
from core.regions import (
    Creek,
    Reach,
    RegionError,
    creek_by_slug,
    creeks_from_regions,
    place_spot,
    reaches_below,
    slugify,
)

ROOT = Path(__file__).resolve().parents[2]


def bay_area() -> dict:
    path = ROOT / "content" / "regions" / "california-bay-area.yaml"
    return {"california-bay-area": yaml.safe_load(path.read_text(encoding="utf-8"))}


def spot(lat: float | None, lon: float | None, *, coarse: bool, name: str = "A spot") -> Spot:
    return Spot(
        spot_id="spot-x",
        spot_name=name,
        reach_id="reach-x",
        reach_name=name,
        creek_id="creek-x",
        creek_name=name,
        latitude=lat,
        longitude=lon,
        coarse=coarse,
    )


def test_the_bay_area_pack_loads_and_strawberry_creek_runs_to_the_bay() -> None:
    creeks = creeks_from_regions(bay_area())
    strawberry = creek_by_slug("strawberry-creek", creeks)
    assert strawberry is not None and strawberry.name == "Strawberry Creek"
    top = strawberry.reach("south-fork-canyon")
    assert top is not None
    below = [r.slug for r in reaches_below(top, strawberry)]
    assert below == [
        "south-fork-campus",
        "campus-west",
        "downtown-culvert",
        "strawberry-creek-park",
        "west-culvert",
    ]
    bottom = strawberry.reach("west-culvert")
    assert bottom is not None and bottom.flows_into is None
    assert reaches_below(bottom, strawberry) == []
    # The two forks meet: both flow into the same reach.
    north = strawberry.reach("north-fork-campus")
    assert north is not None and north.flows_into == "campus-west"


def test_a_precise_pin_is_placed_on_its_reach_and_a_coarse_pin_on_the_creek_only() -> None:
    creeks = creeks_from_regions(bay_area())
    # Faculty Glade, on the South Fork through the central campus.
    precise = place_spot(spot(37.8716, -122.2560, coarse=False), creeks)
    assert precise is not None
    assert precise.creek.slug == "strawberry-creek"
    assert precise.reach is not None and precise.reach.slug == "south-fork-campus"
    # The same point rounded to about a kilometre: the creek is known, the reach is not.
    coarse = place_spot(spot(37.87, -122.26, coarse=True), creeks)
    assert coarse is not None and coarse.creek.slug == "strawberry-creek"
    assert coarse.reach is None, "a box a few hundred metres across says nothing about a coarse pin"
    # Unless the person named the reach.
    named = place_spot(spot(37.87, -122.26, coarse=True, name="Strawberry Creek Park"), creeks)
    assert named is not None and named.reach is not None
    assert named.reach.slug == "strawberry-creek-park"


def test_a_pin_far_away_or_without_a_name_is_placed_nowhere() -> None:
    creeks = creeks_from_regions(bay_area())
    assert place_spot(spot(37.89, -122.28, coarse=False, name="Codornices Creek"), creeks) is None
    assert place_spot(spot(None, None, coarse=True, name="Somewhere"), creeks) is None
    # No coordinates, but the creek is in the name.
    by_name = place_spot(spot(None, None, coarse=True, name="Strawberry Creek footbridge"), creeks)
    assert by_name is not None and by_name.creek.slug == "strawberry-creek"
    assert by_name.reach is None


def test_the_first_box_that_holds_a_precise_pin_wins() -> None:
    creeks = creeks_from_regions(bay_area())
    # The forks share a longitude range and are told apart by latitude alone.
    south = place_spot(spot(37.8720, -122.2600, coarse=False), creeks)
    north = place_spot(spot(37.8750, -122.2600, coarse=False), creeks)
    assert south is not None and south.reach is not None and south.reach.slug == "south-fork-campus"
    assert north is not None and north.reach is not None and north.reach.slug == "north-fork-campus"


# A broken pack fails at load time, with the line named.


def pack(reaches: list[dict], slug: str = "test-creek") -> dict:
    return {"r": {"creeks": [{"slug": slug, "name": "Test Creek", "reaches": reaches}]}}


def test_flows_into_must_name_a_reach_of_the_same_creek() -> None:
    with pytest.raises(RegionError, match="flows_into 'nowhere' is not a reach"):
        creeks_from_regions(pack([{"slug": "a", "name": "A", "flows_into": "nowhere"}]))


def test_reaches_may_not_flow_in_a_circle() -> None:
    with pytest.raises(RegionError, match="circle"):
        creeks_from_regions(
            pack(
                [
                    {"slug": "a", "name": "A", "flows_into": "b"},
                    {"slug": "b", "name": "B", "flows_into": "a"},
                ]
            )
        )
    with pytest.raises(RegionError, match="flows into itself"):
        creeks_from_regions(pack([{"slug": "a", "name": "A", "flows_into": "a"}]))


def test_slugs_are_readable_and_unique() -> None:
    with pytest.raises(RegionError, match="lower case"):
        creeks_from_regions(pack([], slug="Strawberry Creek"))
    with pytest.raises(RegionError, match="appears twice"):
        creeks_from_regions(pack([{"slug": "a", "name": "A"}, {"slug": "a", "name": "A again"}]))
    two = {"r": {"creeks": [{"slug": "x", "name": "X"}, {"slug": "x", "name": "X again"}]}}
    with pytest.raises(RegionError, match="appears twice"):
        creeks_from_regions(two)


def test_a_bbox_is_four_numbers_south_west_north_east() -> None:
    with pytest.raises(RegionError, match="south, west, north, east"):
        creeks_from_regions(pack([{"slug": "a", "name": "A", "bbox": [1, 2, 3]}]))
    with pytest.raises(RegionError, match="south < north"):
        creeks_from_regions(pack([{"slug": "a", "name": "A", "bbox": [38, -122, 37, -121]}]))
    ok = creeks_from_regions(pack([{"slug": "a", "name": "A", "bbox": [37, -122, 38, -121]}]))
    assert ok[0].reaches[0].bbox == (37.0, -122.0, 38.0, -121.0)
    assert ok[0].bbox() == (37.0, -122.0, 38.0, -121.0)
    assert Creek(slug="empty", name="Empty").bbox() is None
    assert not Reach(slug="r", name="R", creek_slug="empty").contains(37.5, -121.5)


def test_slugify_makes_a_readable_link_id() -> None:
    assert slugify("Heraklion") == "heraklion"
    assert slugify("  Strawberry Creek ") == "strawberry-creek"
    assert slugify("Heraklion, Crete (GR)") == "heraklion-crete-gr"
    assert slugify("Codornices Creek 2") == "codornices-creek-2"
    with pytest.raises(RegionError, match="no letters"):
        slugify("...")
