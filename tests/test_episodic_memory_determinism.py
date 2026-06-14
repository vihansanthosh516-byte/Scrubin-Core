"""Deterministic replay test for Episodic Memory (Phase 3.1).

Runs two orchestrators with the same seed and verifies that the
episodic memory store produces identical episodes, hashes, ordering,
statistics, and query results.
"""

import pytest

from scrubin.core.orchestrator import Orchestrator
from scrubin.core.config import ConfigLayer
from scrubin.cognition.memory_statistics import episode_count, mean_importance


def _run_orchestrator(seed: int, ticks: int) -> Orchestrator:
    cfg = ConfigLayer(active_profile="default")
    orch = Orchestrator(seed=seed, config=cfg, active_profile="default", mode="autonomous")
    # Ensure any initialization that publishes boot events is performed.
    orch.setup()
    for _ in range(ticks):
        orch.tick()
    return orch


def test_episodic_memory_deterministic_replay():
    seed = 42
    ticks = 10

    orch_a = _run_orchestrator(seed, ticks)
    orch_b = _run_orchestrator(seed, ticks)

    eps_a = orch_a.memory_store.episodes
    eps_b = orch_b.memory_store.episodes

    # Same count and deterministic IDs
    assert len(eps_a) == len(eps_b) == ticks
    assert [ep.id for ep in eps_a] == [ep.id for ep in eps_b]

    # Compare per‑episode deterministic fields
    for ep_a, ep_b in zip(eps_a, eps_b):
        assert ep_a.tick == ep_b.tick
        assert ep_a.replay_hash == ep_b.replay_hash
        # Importance must be identical
        assert ep_a.importance == ep_b.importance
        # Event ID ordering must be identical
        assert ep_a.event_ids == ep_b.event_ids

    # Memory statistics must match
    assert episode_count(orch_a.memory_store) == episode_count(orch_b.memory_store) == ticks
    assert mean_importance(orch_a.memory_store) == mean_importance(orch_b.memory_store)

    # Deterministic query – episodes after tick 5
    after_tick = 5
    q_a = orch_a.memory_store.query(after_tick=after_tick)
    q_b = orch_b.memory_store.query(after_tick=after_tick)
    assert [ep.id for ep in q_a] == [ep.id for ep in q_b]
    assert [ep.tick for ep in q_a] == [ep.tick for ep in q_b]
