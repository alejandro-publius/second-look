"""Video walks: a guided creek check made while watching an openly licensed clip (Update 14 3.7).

Pure functions. A walk visit is built on the person's own device from their answers and is never
sent to our store, so it is never counted and never mirrored to the sandbox. Every resource in
its Bundle carries a demo tag, and its spot, reach and creek ids all start with "walk-", so no
stored visit can ever collide with one.

The walk itself (the clip, its credit, and the flags the checker raised on its frames at build
time) is a row of content/walks.yaml, written by scripts/build_walks.py.
"""

from __future__ import annotations

import copy
import hashlib
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from core.fhir_emit import REPO_URL, emit_visit
from core.records import Observer, Spot, VisitRecord

DEMO_TAG_SYSTEM = f"{REPO_URL}/tags"
DEMO_TAG_CODE = "demo-walk"
DEMO_TAG_DISPLAY = "Demo visit from a video walk. Made on the device, never stored or counted."
WALK_PREFIX = "walk-"


def walk_spot(walk: Mapping[str, Any]) -> Spot:
    """The one spot a walk has. No position: a clip is not a place anyone stood with a phone."""
    wid = f"{WALK_PREFIX}{walk['id']}"
    return Spot(
        spot_id=f"{wid}-spot",
        spot_name=str(walk["spot_name"]),
        reach_id=f"{wid}-reach",
        reach_name=str(walk["spot_name"]),
        creek_id=wid,
        creek_name=str(walk["creek_name"]),
        latitude=None,
        longitude=None,
        coarse=True,
    )


def utc_stamp(moment: datetime) -> str:
    """Seconds in UTC with a Z, the one spelling both languages write the same way."""
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def walk_visit_id(walk_id: str, answered_at: datetime) -> str:
    """Deterministic: the walk and the moment. Answers stay out, so no float ever gets hashed."""
    blob = f"{walk_id}|{utc_stamp(answered_at)}"
    return WALK_PREFIX + hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def walk_visit(
    walk: Mapping[str, Any], answers: Mapping[str, Any], answered_at: datetime
) -> VisitRecord:
    return VisitRecord(
        visit_id=walk_visit_id(str(walk["id"]), answered_at),
        spot=walk_spot(walk),
        observer=Observer(contributor_token=f"demo-walk-{walk['id']}"),
        answered_at=answered_at,
        answers=dict(answers),
    )


def tag_demo(bundle: Mapping[str, Any]) -> dict[str, Any]:
    """A copy of the Bundle with the demo tag on the Bundle and on every resource in it."""
    out = copy.deepcopy(dict(bundle))
    tag = {"system": DEMO_TAG_SYSTEM, "code": DEMO_TAG_CODE, "display": DEMO_TAG_DISPLAY}
    for node in [out, *(e["resource"] for e in out.get("entry", []))]:
        meta = node.setdefault("meta", {})
        tags = [t for t in meta.get("tag", []) if t.get("system") != DEMO_TAG_SYSTEM]
        tags.append(dict(tag))
        meta["tag"] = tags
    return out


def walk_bundle(
    walk: Mapping[str, Any], answers: Mapping[str, Any], answered_at: datetime
) -> dict[str, Any]:
    """The FHIR record of one walk visit, tagged as a demo."""
    visit = walk_visit(walk, answers, answered_at)
    return tag_demo(emit_visit(visit, test_sitting=None, emitted_at=answered_at))


def is_demo(bundle: Mapping[str, Any]) -> bool:
    """True when a Bundle carries the demo tag. The sandbox mirror refuses these."""
    tags = bundle.get("meta", {}).get("tag", [])
    return any(t.get("system") == DEMO_TAG_SYSTEM and t.get("code") == DEMO_TAG_CODE for t in tags)
