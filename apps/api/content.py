"""The content files, loaded once. The gold key stays on this side of the network."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from apps.api.settings import settings
from core.content_loader import Content, load_content
from core.records import GoldLabel

log = logging.getLogger("apps.api")


@lru_cache(maxsize=1)
def get_content() -> Content:
    """Loads content/ and photos/manifest.csv from settings.content_root. Fails loudly on a
    broken key: a study must not run on a test set that does not add up."""
    content = load_content(settings.content_root, strict=True)
    log.info(
        "content loaded: %d test items, %d form items, hash %s",
        len(content.test_items),
        len(content.form.get("items", [])),
        content.content_hash(),
    )
    return content


def test_item_ids() -> list[str]:
    return [str(item["id"]) for item in get_content().test_items]


def gold_for(item_id: str) -> GoldLabel | None:
    for item in get_content().test_items:
        if str(item["id"]) == item_id:
            gold: GoldLabel = item["gold"]
            return gold
    return None


def feature_for_test_item(item_id: str) -> str | None:
    for item in get_content().test_items:
        if str(item["id"]) == item_id:
            return str(item["feature"])
    return None


@lru_cache(maxsize=1)
def warmup_ids() -> frozenset[str]:
    import yaml

    path = get_content().root / "content" / "test_items.yaml"
    with path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return frozenset(str(w["id"]) for w in raw.get("warmup", []))


@lru_cache(maxsize=1)
def walks() -> tuple[dict[str, str], ...]:
    """The video walks a finished walk may name (content/walks.yaml): id, spot and creek names.

    Only what the record needs. The clip, its credit and the checker's flags stay in the file.
    """
    import yaml

    path = get_content().root / "content" / "walks.yaml"
    if not path.exists():
        return ()
    with path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return tuple(
        {"id": str(w["id"]), "spot_name": str(w["spot_name"]), "creek_name": str(w["creek_name"])}
        for w in raw.get("walks", []) or []
    )


def walk_by_id(walk_id: str) -> dict[str, str] | None:
    for walk in walks():
        if walk["id"] == walk_id:
            return walk
    return None


def form_items() -> list[dict[str, Any]]:
    return list(get_content().form.get("items", []))


def form_item(item_id: str) -> dict[str, Any] | None:
    for item in form_items():
        if item.get("id") == item_id:
            return item
    return None


def feature_name(feature_id: str) -> str:
    for f in get_content().features:
        if f.get("id") == feature_id:
            return str(f.get("name", feature_id))
    return feature_id


def region_plant_names() -> set[str]:
    names: set[str] = set()
    for region in get_content().regions.values():
        for plant in region.get("invasive_plants", []) or []:
            if plant.get("common_name"):
                names.add(str(plant["common_name"]))
            if plant.get("latin_name"):
                names.add(str(plant["latin_name"]))
    return names
