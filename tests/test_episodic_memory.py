"""Tests for the deterministic episodic memory engine (Phase 3.1).

The tests verify that:
* An Episode is created for each tick.
* Episode IDs are deterministic (based on tick).
* Replay hashes are identical across re‑runs with the same seed.
"""

import pytest

from scrubin.core.orchestrator import Orchestrator
from scrubin.core.config import ConfigLayer


def run_ticks(orch: Orchestrator, n: int):
    """Utility to run ``n`` ticks on the orchestrator."""
    for _ in range(n):
        orch.tick()


def test_episode_created_per_tick():
    cfg = ConfigLayer(active_profile="default")
    orch = Orchestrator(seed=0, config=cfg, active_profile="default", mode="autonomous")
    orch.setup()
    run_ticks(orch, 3)
    # Expect three episodes, IDs ``episode-1`` … ``episode-3``
    episodes = orch.memory_store.episodes
    assert len(episodes) == 3
    for i, ep in enumerate(episodes, start=1):
        assert ep.id == f"episode-{i}"
        assert ep.tick == i


def test_episode_hash_deterministic():
    cfg = ConfigLayer(active_profile="default")
    orch1 = Orchestrator(seed=0, config=cfg, active_profile="default", mode="autonomous")
    orch1.setup()
    run_ticks(orch1, 5)
    hashes1 = [ep.replay_hash for ep in orch1.memory_store.episodes]

    orch2 = Orchestrator(seed=0, config=cfg, active_profile="default", mode="autonomous")
    orch2.setup()
    run_ticks(orch2, 5)
    hashes2 = [ep.replay_hash for ep in orch2.memory_store.episodes]

    assert hashes1 == hashes2
