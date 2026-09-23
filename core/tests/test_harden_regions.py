"""A broken region pack fails with the line named, and creeks answer only for what they hold."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from hypothesis import given, settings
from hypothesis import strategies as st

from core.records import Spot
from core.regions import (
    Creek,
    Reach,
    RegionError,
    creek_by_slug,
    creeks_from_regions,
    place_spot,
    reaches_below,
)

ROOT = Path(__file__).resolve().parents[2]
REGIONS_DIR = ROOT / "content" / "regions"


def real_packs() -> dict[str, dict[str, Any]]:
    """Every committed region pack, keyed by its file name, as the app would load them."""
    packs: dict[str, dict[str, Any]] = {}
    for path in sorted(REGIONS_DIR.glob("*.yaml")):
        packs[path.stem] = yaml.safe_load(path.read_text(encoding="utf-8"))
    return packs


def one_creek(creek: dict[str, Any], region: str = "r") -> dict[str, Any]:
    return {region: {"creeks": [creek]}}


def with_reaches(reaches: list[dict[str, Any]]) -> dict[str, Any]:
    return one_creek({"slug": "test-creek", "name": "Test Creek", "reaches": reaches})


def spot(lat: float | None, lon: float | None, *, name: str, coarse: bool = False) -> Spot:
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


# The real packs in content/regions.


def test_every_committed_region_pack_loads_together_and_every_reach_runs_to_a_bottom() -> None:
    packs = real_packs()
    assert {"california-bay-area", "heraklion"} <= set(packs)
    creeks = creeks_from_regions(packs)
    assert creeks, "the Bay Area pack names at least one creek"
    # The Heraklion stub has no creeks yet, so every creek comes from another pack.
    assert packs["heraklion"]["creeks"] == []
    for creek in creeks:
        assert creek.reaches, f"{creek.slug} lists its reaches"
        for reach in creek.reaches:
            assert reach.creek_slug == creek.slug
            assert creek.reach(reach.slug) is reach
            below = reaches_below(reach, creek)
            last = below[-1] if below else reach
            assert last.flows_into is None, f"{reach.slug} ends at the bottom of {creek.slug}"
            assert reach not in below


def test_every_reach_box_in_the_real_packs_sits_inside_its_creek_box() -> None:
    for creek in creeks_from_regions(real_packs()):
        for reach in creek.reaches:
            assert reach.bbox is not None, f"{creek.slug}/{reach.slug} has a box"
            south, west, north, east = reach.bbox
            for lat, lon in [(south, west), (south, east), (north, west), (north, east)]:
                assert reach.contains(lat, lon)
                assert creek.contains(lat, lon)


def test_a_real_creek_says_it_has_no_reach_by_a_slug_it_does_not_list() -> None:
    strawberry = creek_by_slug("strawberry-creek", creeks_from_regions(real_packs()))
    assert strawberry is not None
    assert strawberry.reach("codornices-upper") is None
    assert strawberry.reach("") is None
    # Slugs match exactly: the reach name is not a slug.
    assert strawberry.reach("Strawberry Creek Park") is None
    assert strawberry.reach("strawberry-creek-park") is not None


def test_a_creek_slug_no_pack_lists_finds_no_creek() -> None:
    creeks = creeks_from_regions(real_packs())
    assert creek_by_slug("codornices-creek", creeks) is None
    assert creek_by_slug("Strawberry Creek", creeks) is None
    assert creek_by_slug("strawberry-creek", []) is None


# Creek.reach and Creek.contains on hand-made creeks.


def test_a_creek_with_no_reaches_has_no_reach_to_give() -> None:
    assert Creek(slug="empty", name="Empty").reach("anything") is None


def test_a_creek_whose_reaches_have_no_boxes_holds_no_point() -> None:
    creek = Creek(
        slug="boxless",
        name="Boxless Creek",
        reaches=(
            Reach(slug="upper", name="Upper", creek_slug="boxless", flows_into="lower"),
            Reach(slug="lower", name="Lower", creek_slug="boxless"),
        ),
    )
    assert creek.bbox() is None
    for lat, lon in [(0.0, 0.0), (37.87, -122.26), (-90.0, -180.0), (90.0, 180.0)]:
        assert creek.contains(lat, lon) is False


def test_a_creek_without_boxes_is_found_by_name_and_never_by_a_pin() -> None:
    creeks = creeks_from_regions(
        one_creek(
            {
                "slug": "boxless",
                "name": "Boxless Creek",
                "reaches": [{"slug": "upper", "name": "Upper meadow"}],
            }
        )
    )
    # A precise pin anywhere cannot land on a creek that has no box.
    assert place_spot(spot(37.87, -122.26, name="A bench"), creeks) is None
    # The name still places it, and the reach name picks the reach.
    found = place_spot(spot(37.87, -122.26, name="Boxless Creek, upper meadow"), creeks)
    assert found is not None
    assert found.creek.slug == "boxless"
    assert found.reach is not None and found.reach.slug == "upper"


def test_a_creek_box_is_the_smallest_box_around_all_its_reach_boxes() -> None:
    creek = Creek(
        slug="two-boxes",
        name="Two Boxes",
        reaches=(
            Reach(slug="a", name="A", creek_slug="two-boxes", bbox=(10.0, 20.0, 11.0, 21.0)),
            Reach(slug="b", name="B", creek_slug="two-boxes"),
            Reach(slug="c", name="C", creek_slug="two-boxes", bbox=(12.0, 22.0, 13.0, 23.0)),
        ),
    )
    assert creek.bbox() == (10.0, 20.0, 13.0, 23.0)
    # The gap between the two reach boxes is inside the creek box, but in no reach box.
    assert creek.contains(11.5, 21.5)
    assert not any(r.contains(11.5, 21.5) for r in creek.reaches)
    # The edges count as inside; one step past any edge does not.
    assert creek.contains(10.0, 20.0) and creek.contains(13.0, 23.0)
    assert not creek.contains(9.999, 21.0)
    assert not creek.contains(13.001, 21.0)
    assert not creek.contains(11.0, 19.999)
    assert not creek.contains(11.0, 23.001)


# A broken pack fails at load time, and the message names the region, creek and reach.


@pytest.mark.parametrize(
    "value",
    [["south", -122, 38, -121], [37, None, 38, -121], [37, -122, [38], -121], [37, -122, 38, {}]],
)
def test_a_bbox_that_holds_something_not_a_number_is_refused(value: list[Any]) -> None:
    with pytest.raises(RegionError) as info:
        creeks_from_regions(with_reaches([{"slug": "a", "name": "A", "bbox": value}]))
    assert str(info.value) == (
        "region r, creek 'test-creek', reach 'a': bbox holds something that is not a number"
    )
    assert isinstance(info.value.__cause__, TypeError | ValueError)


def test_a_bbox_given_as_numbers_in_text_is_read_as_numbers() -> None:
    creeks = creeks_from_regions(
        with_reaches([{"slug": "a", "name": "A", "bbox": ["37", "-122", "38.5", "-121"]}])
    )
    assert creeks[0].reaches[0].bbox == (37.0, -122.0, 38.5, -121.0)


@pytest.mark.parametrize(
    "value",
    [
        [-91, -122, 38, -121],
        [37, -122, 91, -121],
        [37, -181, 38, -121],
        [37, -122, 38, 181],
        [37, -122, 37, -121],
        [37, -121, 38, -121],
        [float("nan"), -122, 38, -121],
    ],
)
def test_a_bbox_off_the_globe_or_with_no_area_is_refused(value: list[float]) -> None:
    with pytest.raises(RegionError, match="reach 'a': bbox is not south < north and west < east"):
        creeks_from_regions(with_reaches([{"slug": "a", "name": "A", "bbox": value}]))


@pytest.mark.parametrize("raw", [{}, {"name": None}, {"name": ""}, {"name": "   "}, {"name": 5}])
def test_a_creek_needs_a_name(raw: dict[str, Any]) -> None:
    with pytest.raises(RegionError) as info:
        creeks_from_regions(one_creek({"slug": "nameless", **raw}, region="north"))
    assert str(info.value) == "region north, creek 'nameless': needs a name"


@pytest.mark.parametrize("rslug", [None, "", "Upper", "upper reach", "-upper", "upper-", 7])
def test_a_reach_slug_must_be_lower_case_letters_digits_and_hyphens(rslug: object) -> None:
    with pytest.raises(RegionError) as info:
        creeks_from_regions(with_reaches([{"slug": rslug, "name": "Upper"}]))
    assert str(info.value) == (
        f"region r, creek 'test-creek', reach {rslug!r}: "
        "slug must be lower case letters, digits and hyphens"
    )


def test_a_reach_with_no_slug_at_all_is_refused_like_a_bad_slug() -> None:
    with pytest.raises(RegionError, match="reach None: slug must be lower case"):
        creeks_from_regions(with_reaches([{"name": "Upper"}]))


@pytest.mark.parametrize("raw", [{}, {"name": None}, {"name": ""}, {"name": " \t"}, {"name": 3}])
def test_a_reach_needs_a_name(raw: dict[str, Any]) -> None:
    with pytest.raises(RegionError) as info:
        creeks_from_regions(with_reaches([{"slug": "upper", **raw}]))
    assert str(info.value) == "region r, creek 'test-creek', reach 'upper': needs a name"


@pytest.mark.parametrize("flows_into", [5, True, ["lower"], {"slug": "lower"}])
def test_flows_into_must_be_a_slug_or_null(flows_into: object) -> None:
    reaches: list[dict[str, Any]] = [
        {"slug": "upper", "name": "Upper", "flows_into": flows_into},
        {"slug": "lower", "name": "Lower"},
    ]
    with pytest.raises(RegionError) as info:
        creeks_from_regions(with_reaches(reaches))
    assert str(info.value) == (
        "region r, creek 'test-creek', reach 'upper': flows_into must be a reach slug or null"
    )


def test_flows_into_null_marks_the_bottom_reach() -> None:
    creeks = creeks_from_regions(
        with_reaches(
            [
                {"slug": "upper", "name": "Upper", "flows_into": "lower"},
                {"slug": "lower", "name": "Lower", "flows_into": None},
            ]
        )
    )
    creek = creeks[0]
    lower = creek.reach("lower")
    upper = creek.reach("upper")
    assert lower is not None and lower.flows_into is None
    assert upper is not None and reaches_below(upper, creek) == [lower]


def test_names_are_trimmed_and_the_source_is_kept_as_text() -> None:
    creeks = creeks_from_regions(
        one_creek(
            {
                "slug": "trim-creek",
                "name": "  Trim Creek \n",
                "source": "Hand filled from public maps.",
                "reaches": [{"slug": "a", "name": "\tUpper reach  "}],
            }
        )
    )
    assert creeks[0].name == "Trim Creek"
    assert creeks[0].source == "Hand filled from public maps."
    assert creeks[0].reaches[0].name == "Upper reach"
    assert creeks[0].reaches[0].bbox is None


def test_a_region_with_no_creeks_or_a_creek_with_no_reaches_loads_empty() -> None:
    regions: dict[str, dict[str, Any]] = {
        "a": {},
        "b": {"creeks": None},
        "c": {"creeks": [{"slug": "bare", "name": "Bare", "reaches": None}]},
    }
    creeks = creeks_from_regions(regions)
    assert [c.slug for c in creeks] == ["bare"]
    assert creeks[0].reaches == ()
    assert creeks_from_regions({}) == []


def test_reach_slugs_repeat_freely_across_creeks_but_creek_slugs_do_not() -> None:
    region = {
        "creeks": [
            {"slug": "east", "name": "East", "reaches": [{"slug": "upper", "name": "Upper"}]},
            {"slug": "west", "name": "West", "reaches": [{"slug": "upper", "name": "Upper"}]},
        ]
    }
    creeks = creeks_from_regions({"r": region})
    assert [(c.slug, c.reaches[0].slug, c.reaches[0].creek_slug) for c in creeks] == [
        ("east", "upper", "east"),
        ("west", "upper", "west"),
    ]


def test_regions_are_read_in_name_order_so_a_clash_names_the_later_region() -> None:
    regions = {
        "zeta": {"creeks": [{"slug": "shared", "name": "Shared in zeta"}]},
        "alpha": {"creeks": [{"slug": "shared", "name": "Shared in alpha"}]},
    }
    with pytest.raises(RegionError) as info:
        creeks_from_regions(regions)
    assert str(info.value) == "region zeta, creek 'shared': slug appears twice"
    # Without the clash, the creeks come back in region name order.
    regions["zeta"]["creeks"][0]["slug"] = "only-zeta"
    assert [c.name for c in creeks_from_regions(regions)] == ["Shared in alpha", "Shared in zeta"]


# reaches_below on a creek built by hand, where the loader's checks never ran.


def test_reaches_below_refuses_a_flows_into_that_names_no_reach() -> None:
    upper = Reach(slug="upper", name="Upper", creek_slug="hand", flows_into="gone")
    creek = Creek(slug="hand", name="Hand Creek", reaches=(upper,))
    with pytest.raises(RegionError) as info:
        reaches_below(upper, creek)
    assert str(info.value) == "creek hand: reach 'gone' does not exist"


def test_reaches_below_stops_where_the_chain_breaks_partway_down() -> None:
    upper = Reach(slug="upper", name="Upper", creek_slug="hand", flows_into="middle")
    middle = Reach(slug="middle", name="Middle", creek_slug="hand", flows_into="missing")
    creek = Creek(slug="hand", name="Hand Creek", reaches=(upper, middle))
    with pytest.raises(RegionError, match="creek hand: reach 'missing' does not exist"):
        reaches_below(upper, creek)


def test_reaches_below_refuses_a_reach_from_another_creek() -> None:
    stranger = Reach(slug="upper", name="Upper", creek_slug="other", flows_into="lower")
    creek = Creek(
        slug="hand",
        name="Hand Creek",
        reaches=(Reach(slug="upper", name="Upper", creek_slug="hand"),),
    )
    with pytest.raises(RegionError, match="creek hand: reach 'lower' does not exist"):
        reaches_below(stranger, creek)


def test_reaches_below_refuses_a_hand_made_circle() -> None:
    a = Reach(slug="a", name="A", creek_slug="loop", flows_into="b")
    b = Reach(slug="b", name="B", creek_slug="loop", flows_into="c")
    c = Reach(slug="c", name="C", creek_slug="loop", flows_into="b")
    creek = Creek(slug="loop", name="Loop Creek", reaches=(a, b, c))
    with pytest.raises(RegionError) as info:
        reaches_below(a, creek)
    assert str(info.value) == "creek loop: reaches flow in a circle at 'b'"


@settings(max_examples=50, deadline=None, database=None)
@given(n=st.integers(min_value=1, max_value=8), data=st.data())
def test_a_chain_of_reaches_lists_everything_below_nearest_first(
    n: int, data: st.DataObject
) -> None:
    slugs = [f"reach-{i}" for i in range(n)]
    reaches = [
        {"slug": s, "name": f"Reach {i}", "flows_into": slugs[i + 1] if i + 1 < n else None}
        for i, s in enumerate(slugs)
    ]
    # The order of the list in the pack does not matter; flows_into sets the order.
    shuffled = data.draw(st.permutations(reaches))
    creek = creeks_from_regions(with_reaches(list(shuffled)))[0]
    start = data.draw(st.integers(min_value=0, max_value=n - 1))
    top = creek.reach(slugs[start])
    assert top is not None
    assert [r.slug for r in reaches_below(top, creek)] == slugs[start + 1 :]


@settings(max_examples=50, deadline=None, database=None)
@given(n=st.integers(min_value=2, max_value=8), data=st.data())
def test_a_chain_that_turns_back_on_itself_is_refused_at_load(n: int, data: st.DataObject) -> None:
    slugs = [f"reach-{i}" for i in range(n)]
    back_to = data.draw(st.integers(min_value=0, max_value=n - 2))
    reaches = [
        {
            "slug": s,
            "name": f"Reach {i}",
            "flows_into": slugs[i + 1] if i + 1 < n else slugs[back_to],
        }
        for i, s in enumerate(slugs)
    ]
    with pytest.raises(RegionError, match="circle"):
        creeks_from_regions(with_reaches(reaches))
