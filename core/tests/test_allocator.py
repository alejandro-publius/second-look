from collections import Counter

import pytest

from core.allocator import arm_for_position, arm_names, block_contents, replay

SEED = "test-seed-2026"


def _blocks(seed: str, count: int, *, k: int, block: int) -> list[list[str]]:
    arms: list[str] = list(replay(seed, count, k=k, block=block))
    return [arms[i : i + block] for i in range(0, count, block)]


def test_k2_every_complete_block_has_two_of_each_arm():
    for blk in _blocks(SEED, 400, k=2, block=4):
        assert Counter(blk) == {"untrained": 2, "trained": 2}


def test_k2_blocks_are_permuted_not_fixed():
    orders = {tuple(blk) for blk in _blocks(SEED, 400, k=2, block=4)}
    assert len(orders) > 1, "every block came out in the same order"


def test_block_id_is_position_over_block_size():
    for position in range(12):
        _, block_id = arm_for_position(SEED, position)
        assert block_id == position // 4


def test_deterministic_from_the_seed():
    first = replay(SEED, 200)
    second = replay(SEED, 200)
    assert first == second


def test_a_different_seed_gives_a_different_sequence():
    assert replay(SEED, 200) != replay("another-seed", 200)


def test_replay_matches_position_by_position_lookup():
    arms = replay(SEED, 50)
    assert arms == [arm_for_position(SEED, n)[0] for n in range(50)]


def test_k3_blocks_of_4_never_let_one_arm_run_ahead_by_more_than_one():
    for blk in _blocks(SEED, 600, k=3, block=4):
        counts = Counter(blk)
        assert set(counts) <= {"untrained", "trained", "arm_3"}
        assert max(counts.values()) - min(counts.get(a, 0) for a in arm_names(3)) <= 1


def test_k3_every_three_consecutive_blocks_are_exactly_balanced():
    blocks = _blocks(SEED, 600, k=3, block=4)
    for i in range(0, len(blocks) - 2, 3):
        counts = Counter(blocks[i] + blocks[i + 1] + blocks[i + 2])
        assert counts == {"untrained": 4, "trained": 4, "arm_3": 4}


def test_k3_block_of_6_is_exactly_balanced():
    for blk in _blocks(SEED, 300, k=3, block=6):
        assert Counter(blk) == {"untrained": 2, "trained": 2, "arm_3": 2}


def test_block_contents_length_and_names():
    assert len(block_contents(SEED, 0)) == 4
    assert arm_names(2) == ("untrained", "trained")
    assert arm_names(4) == ("untrained", "trained", "arm_3", "arm_4")


def test_bad_arguments_are_refused():
    with pytest.raises(ValueError):
        arm_for_position(SEED, -1)
    with pytest.raises(ValueError):
        arm_names(1)
    with pytest.raises(ValueError):
        block_contents(SEED, 0, block=0)
