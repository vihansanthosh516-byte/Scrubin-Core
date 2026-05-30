"""Hashing utilities test for ``WorldState``.

Ensures that the deterministic hash function is stable across multiple
invocations and that the comparison helper works as expected.
"""

from scrubin.world.state import WorldState
from scrubin.runtime.state_hashing import deterministic_world_hash, compare_world_hashes


def test_deterministic_world_hash_consistency():
    w1 = WorldState(tick=0, seed=0)
    w2 = WorldState(tick=0, seed=0)
    h1 = deterministic_world_hash(w1)
    h2 = deterministic_world_hash(w2)
    assert h1 == h2
    assert compare_world_hashes(w1, w2)


def test_different_world_hashes():
    w1 = WorldState(tick=0, seed=0)
    w2 = WorldState(tick=1, seed=0)
    assert not compare_world_hashes(w1, w2)
