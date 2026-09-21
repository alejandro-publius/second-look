"""Creeks and reaches from the region pack, and where a stored spot sits on them.

The store keeps its own generated ids for a spot's creek and reach (Update 10B answer 2). The
region pack names each creek with a readable slug and lists its reaches by hand, each with a
`flows_into` field and an approximate bounding box. This module joins the two at read time, so a
correction to the pack fixes every old spot too, and nothing in the database has to change.

Placement is deliberately cautious. A precise pin is placed by the first reach box that holds it.
A coarse pin is rounded to about a kilometre before it is stored, so a box a few hundred metres
across says nothing about it: a coarse pin is placed on the creek only, never on a reach, unless
the person named the reach themselves. The downstream note therefore appears only where a reach is
known and its `flows_into` is set.

Pure. No file or network I/O.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from core.records import Frozen, Spot


class RegionError(ValueError):
    """The region pack's creek list does not hold together. The message names the line."""


class Reach(Frozen):
    slug: str
    name: str
    creek_slug: str
    # The reach this one flows into, or None at the bottom of the creek.
    flows_into: str | None = None
    # (south, west, north, east) in degrees, approximate, hand filled. None when unknown.
    bbox: tuple[float, float, float, float] | None = None

    def contains(self, latitude: float, longitude: float) -> bool:
        if self.bbox is None:
            return False
        south, west, north, east = self.bbox
        return south <= latitude <= north and west <= longitude <= east


class Creek(Frozen):
    slug: str
    name: str
    reaches: tuple[Reach, ...] = ()
    source: str = ""

    def reach(self, slug: str) -> Reach | None:
        for r in self.reaches:
            if r.slug == slug:
                return r
        return None

    def bbox(self) -> tuple[float, float, float, float] | None:
        boxes = [r.bbox for r in self.reaches if r.bbox is not None]
        if not boxes:
            return None
        return (
            min(b[0] for b in boxes),
            min(b[1] for b in boxes),
            max(b[2] for b in boxes),
            max(b[3] for b in boxes),
        )

    def contains(self, latitude: float, longitude: float) -> bool:
        box = self.bbox()
        if box is None:
            return False
        south, west, north, east = box
        return south <= latitude <= north and west <= longitude <= east


class Placement(Frozen):
    creek: Creek
    reach: Reach | None = None


def _slug_ok(slug: object) -> bool:
    return (
        isinstance(slug, str)
        and bool(slug)
        and all(ch.islower() or ch.isdigit() or ch == "-" for ch in slug)
        and not slug.startswith("-")
        and not slug.endswith("-")
    )


def _bbox(raw: object, where: str) -> tuple[float, float, float, float] | None:
    if raw is None:
        return None
    if not isinstance(raw, list | tuple) or len(raw) != 4:
        raise RegionError(f"{where}: bbox must be [south, west, north, east]")
    try:
        south, west, north, east = (float(v) for v in raw)
    except (TypeError, ValueError) as exc:
        raise RegionError(f"{where}: bbox holds something that is not a number") from exc
    if not (-90 <= south < north <= 90 and -180 <= west < east <= 180):
        raise RegionError(f"{where}: bbox is not south < north and west < east")
    return (south, west, north, east)


def creeks_from_regions(regions: Mapping[str, Mapping[str, Any]]) -> list[Creek]:
    """Every creek in every region pack, checked so a broken pack fails at load time."""
    creeks: list[Creek] = []
    seen: set[str] = set()
    for region_name, region in sorted(regions.items()):
        for raw in region.get("creeks", []) or []:
            slug = raw.get("slug")
            where = f"region {region_name}, creek {slug!r}"
            if not _slug_ok(slug):
                raise RegionError(f"{where}: slug must be lower case letters, digits and hyphens")
            if slug in seen:
                raise RegionError(f"{where}: slug appears twice")
            seen.add(slug)
            name = raw.get("name")
            if not isinstance(name, str) or not name.strip():
                raise RegionError(f"{where}: needs a name")
            reaches: list[Reach] = []
            reach_slugs: set[str] = set()
            for r in raw.get("reaches", []) or []:
                rslug = r.get("slug")
                rwhere = f"{where}, reach {rslug!r}"
                if not _slug_ok(rslug):
                    raise RegionError(
                        f"{rwhere}: slug must be lower case letters, digits and hyphens"
                    )
                if rslug in reach_slugs:
                    raise RegionError(f"{rwhere}: slug appears twice")
                reach_slugs.add(rslug)
                rname = r.get("name")
                if not isinstance(rname, str) or not rname.strip():
                    raise RegionError(f"{rwhere}: needs a name")
                flows_into = r.get("flows_into")
                if flows_into is not None and not isinstance(flows_into, str):
                    raise RegionError(f"{rwhere}: flows_into must be a reach slug or null")
                reaches.append(
                    Reach(
                        slug=rslug,
                        name=rname.strip(),
                        creek_slug=slug,
                        flows_into=flows_into,
                        bbox=_bbox(r.get("bbox"), rwhere),
                    )
                )
            for reach in reaches:
                if reach.flows_into is not None and reach.flows_into not in reach_slugs:
                    raise RegionError(
                        f"{where}, reach {reach.slug!r}: flows_into {reach.flows_into!r} "
                        "is not a reach of this creek"
                    )
                if reach.flows_into == reach.slug:
                    raise RegionError(f"{where}, reach {reach.slug!r}: flows into itself")
            creek = Creek(
                slug=slug,
                name=name.strip(),
                reaches=tuple(reaches),
                source=str(raw.get("source", "")),
            )
            for reach in reaches:
                reaches_below(reach, creek)  # raises on a cycle
            creeks.append(creek)
    return creeks


def creek_by_slug(slug: str, creeks: Iterable[Creek]) -> Creek | None:
    for c in creeks:
        if c.slug == slug:
            return c
    return None


def reaches_below(reach: Reach, creek: Creek) -> list[Reach]:
    """Every reach downstream of this one, nearest first, following flows_into to the end."""
    out: list[Reach] = []
    seen = {reach.slug}
    current = reach
    while current.flows_into is not None:
        nxt = creek.reach(current.flows_into)
        if nxt is None:
            raise RegionError(f"creek {creek.slug}: reach {current.flows_into!r} does not exist")
        if nxt.slug in seen:
            raise RegionError(f"creek {creek.slug}: reaches flow in a circle at {nxt.slug!r}")
        seen.add(nxt.slug)
        out.append(nxt)
        current = nxt
    return out


def _named(text: str, name: str) -> bool:
    return name.lower() in text.lower()


def place_spot(spot: Spot, creeks: Sequence[Creek]) -> Placement | None:
    """Which creek, and which reach, a stored spot sits on. None when no creek claims it.

    Order: a precise pin inside a reach box; then any pin inside a creek box; then the creek's
    name inside the spot's creek name or spot name. A reach is named only by a precise pin's box,
    or by the reach name appearing in the spot's reach name or spot name.
    """
    lat, lon = spot.latitude, spot.longitude
    if lat is not None and lon is not None:
        if not spot.coarse:
            for creek in creeks:
                for reach in creek.reaches:
                    if reach.contains(lat, lon):
                        return Placement(creek=creek, reach=reach)
        for creek in creeks:
            if creek.contains(lat, lon):
                return Placement(creek=creek, reach=_reach_by_name(spot, creek))
    for creek in creeks:
        if _named(spot.creek_name, creek.name) or _named(spot.spot_name, creek.name):
            return Placement(creek=creek, reach=_reach_by_name(spot, creek))
    return None


def _reach_by_name(spot: Spot, creek: Creek) -> Reach | None:
    for reach in creek.reaches:
        if _named(spot.reach_name, reach.name) or _named(spot.spot_name, reach.name):
            return reach
    return None
