"""The health card: one approved action each for the person, the pet and the city (hard rule 5).

Every sentence comes from content/approved_sentences.yaml and only when approved is exactly True
and a source is present. Code picks by a seeded hash so the same seed gives the same card. With
any audience empty there is no card at all.

Pure. No file or network I/O.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from typing import Any

from core.records import Frozen

AUDIENCES = ("person", "pet", "city")


class HealthCard(Frozen):
    """Three approved sentences and their three sources, in audience order."""

    person: str
    pet: str
    city: str
    sources: tuple[str, str, str]


def _eligible(sentence: Mapping[str, Any]) -> bool:
    text = sentence.get("text")
    source = sentence.get("source")
    return (
        sentence.get("approved") is True
        and isinstance(text, str)
        and bool(text.strip())
        and isinstance(source, str)
        and bool(source.strip())
        and sentence.get("audience") in AUDIENCES
    )


def _pick_index(seed: str, audience: str, count: int) -> int:
    digest = hashlib.sha256(f"{seed}:{audience}".encode()).digest()
    return int.from_bytes(digest[:8], "big") % count


def pick_actions(sentences: Sequence[Mapping[str, Any]], seed: str) -> HealthCard | None:
    """Only sentences with approved == True. One per audience, chosen by a seeded pick.

    None if any audience has none.
    """
    chosen: dict[str, tuple[str, str]] = {}
    for audience in AUDIENCES:
        pool = sorted(
            (s for s in sentences if _eligible(s) and s.get("audience") == audience),
            key=lambda s: (str(s.get("id", "")), str(s["text"])),
        )
        if not pool:
            return None
        pick = pool[_pick_index(seed, audience, len(pool))]
        chosen[audience] = (str(pick["text"]).strip(), str(pick["source"]).strip())
    return HealthCard(
        person=chosen["person"][0],
        pet=chosen["pet"][0],
        city=chosen["city"][0],
        sources=(chosen["person"][1], chosen["pet"][1], chosen["city"][1]),
    )
