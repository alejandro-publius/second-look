"""Permuted block randomization. Pure and deterministic from a seed, so it can be replayed.

The API keeps one counter row. The nth randomized session (position n, counting from 0)
gets the arm at slot n of the sequence this module defines. Nothing here touches a database.

Blocks: positions 0 to block-1 form block 0, the next `block` positions form block 1, and so on.
Inside a block each arm appears block // k times. When block is not a multiple of k, the
block % k spare slots go to arms chosen by a fixed rotation over block ids, so every run of
k consecutive blocks is exactly balanced and no arm is ever more than one slot ahead within
a block. For k = 2 and block = 4 every block is exactly 2 and 2.
"""

from __future__ import annotations

import hashlib
import random
from typing import cast

from core.records import Arm

ARM_NAMES: tuple[str, ...] = ("untrained", "trained")


def arm_names(k: int) -> tuple[str, ...]:
    """The arm labels for k arms: untrained, trained, then arm_3, arm_4 and so on."""
    if k < 2:
        raise ValueError("k must be at least 2")
    return ARM_NAMES[:k] + tuple(f"arm_{i}" for i in range(len(ARM_NAMES) + 1, k + 1))


def _rng(seed: str, block_id: int) -> random.Random:
    digest = hashlib.sha256(f"{seed}|block|{block_id}".encode()).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def block_contents(seed: str, block_id: int, *, k: int = 2, block: int = 4) -> tuple[str, ...]:
    """The permuted arms of one block, in slot order."""
    if block < 1:
        raise ValueError("block must be at least 1")
    if block_id < 0:
        raise ValueError("block_id must be 0 or more")
    names = arm_names(k)
    slots: list[str] = list(names) * (block // k)
    spare = block % k
    if spare:
        # Rotate which arms get the spare slots so k consecutive blocks are exactly balanced.
        start = (block_id * spare) % k
        slots.extend(names[(start + i) % k] for i in range(spare))
    _rng(seed, block_id).shuffle(slots)
    return tuple(slots)


def arm_for_position(seed: str, position: int, *, k: int = 2, block: int = 4) -> tuple[Arm, int]:
    """Deterministic: the arm and block id for the nth randomized session (n from 0).

    Permuted blocks of `block` over `k` arms. For k > 2 the extra arms are named arm_3,
    arm_4 and so on; they are returned through the same Arm type on purpose, so a third arm
    can be added later without changing callers.
    """
    if position < 0:
        raise ValueError("position must be 0 or more")
    block_id = position // block
    slot = position % block
    arm = block_contents(seed, block_id, k=k, block=block)[slot]
    return cast(Arm, arm), block_id


def replay(seed: str, count: int, *, k: int = 2, block: int = 4) -> list[Arm]:
    """The first `count` arms of the sequence, so an analyst can check stored assignments."""
    return [arm_for_position(seed, n, k=k, block=block)[0] for n in range(count)]
