"""Part 2, the assisted second look: when the checker's question appears, and what is stored.

Pure. No file or network I/O. The Worker runs a port of this (worker/src/core/assist.ts), proved
equal by the golden vectors in worker/golden/assist.json.

Two rules, and the second is why this module exists (hard rule 2, UPDATE_31 section 3):

- question_needed: in the assisted arm, when the item's precomputed flag points the other way from
  the person's first answer, one question appears. A Can't tell answer disagrees with any flag.
  The flag never says which way it points.
- settle: the stored final answer is the person's first answer, or the answer the person picked
  after pressing Change. The flag is not a parameter, so it cannot set or change an answer.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

ANSWERS = ("yes", "no", "cant_tell")
ARMS = ("unassisted", "assisted")
SIDES = ("present", "absent")
CHOICES = ("keep", "change")
QUESTION = "The checker noticed something here. Look again?"
# The slot sequence comes from core.allocator, whose two arm names are part 1's. Part 2 reads
# them through this map, so the allocator stays the single source of truth for randomization.
ALLOCATOR_TO_PART2 = {"untrained": "unassisted", "trained": "assisted"}


class AssistError(ValueError):
    """An answer or a choice that cannot be stored. The message is plain words."""


def side_answer(side: str) -> str:
    """The answer a flag pointing at this side agrees with."""
    return "yes" if side == "present" else "no"


def flag_side(flags: object, item_id: object) -> str | None:
    """The side the committed flag for this item points at, or None.

    Reads results/assist_flags.json defensively: anything that is not an item entry whose flag
    points at present or absent gives no flag, so malformed content can only remove a question.
    """
    if not isinstance(flags, Mapping) or not isinstance(item_id, str):
        return None
    items = flags.get("items")
    if not isinstance(items, list):
        return None
    for entry in items:
        if not isinstance(entry, Mapping) or entry.get("item_id") != item_id:
            continue
        flag = entry.get("flag")
        if isinstance(flag, Mapping) and flag.get("points_to") in SIDES:
            return str(flag["points_to"])
        return None
    return None


def question_needed(arm: object, side: object, first: object) -> bool:
    """True only in the assisted arm, for a real flag that disagrees with the first answer."""
    if arm != "assisted" or side not in SIDES or first not in ANSWERS:
        return False
    return first != side_answer(str(side))


@dataclass(frozen=True)
class Settled:
    first_answer: str
    final_answer: str
    question_shown: bool
    choice: str  # "" when no question was shown


def settle(
    first: object, *, asked: bool, choice: object = None, changed_to: object = None
) -> Settled:
    """The stored row for one item. Raises AssistError for anything the person did not do."""
    if first not in ANSWERS:
        raise AssistError("We do not know that answer.")
    first_s = str(first)
    if not asked:
        if choice not in (None, "") or changed_to not in (None, ""):
            raise AssistError(
                "No question was asked for this photo, so there is nothing to choose."
            )
        return Settled(first_s, first_s, False, "")
    if choice == "keep":
        if changed_to not in (None, "", first_s):
            raise AssistError("Keep keeps the first answer.")
        return Settled(first_s, first_s, True, "keep")
    if choice == "change":
        if changed_to not in ANSWERS:
            raise AssistError("We do not know that answer.")
        return Settled(first_s, str(changed_to), True, "change")
    raise AssistError("Choose Keep or Change.")


def score(finals: Mapping[str, Any], gold: Mapping[str, str]) -> int:
    """Items right with the final answer. Can't tell is never right."""
    return sum(
        1 for item, answer in finals.items() if item in gold and answer == side_answer(gold[item])
    )
