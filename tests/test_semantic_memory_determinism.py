"""Deterministic Semantic Memory tests (Phase 3.2).

These tests verify that facts built from episodes are:
* deterministic in ID and hash
* correctly merged across multiple supporting episodes
* have Laplace‑smoothed confidence
* support O(1) exact look‑ups and deterministic query ordering.
"""

import pytest

from scrubin.cognition.fact_store import FactStore
from scrubin.cognition.fact_builder import process_episode
from scrubin.memory.episode import Episode, ActionSummary, ConsequenceSummary, Observation


def make_simple_episode(eid: str, tick: int) -> Episode:
    """Create an episode with a single action and a single consequence.

    The action "apply_pressure" is linked to the consequence "bleeding_decrease".
    """
    action = ActionSummary(name="apply_pressure", agent="unit_test", tick=tick)
    consequence = ConsequenceSummary(name="bleeding_decrease", severity=0.5, tick=tick)
    return Episode(
        id=eid,
        tick=tick,
        phase="main",
        participants=("unit_test",),
        observations=(),
        actions=(action,),
        consequences=(consequence,),
        outcome="completed",
        importance=0.0,
        event_ids=(),
        replay_hash="",
    )


def test_fact_creation_and_merge():
    store = FactStore()
    # Process three identical episodes – fact should be merged with support_count=3
    for i in range(1, 4):
        ep = make_simple_episode(eid=f"episode-{i}", tick=i)
        process_episode(ep, store)

    # Exactly one fact should exist
    assert store.fact_count() == 1
    fact = store.facts[0]
    # Deterministic ID format "fact-<12hex>"
    assert fact.id.startswith("fact-") and len(fact.id) == 17
    # Support count reflects three episodes
    assert fact.support_count == 3
    # Supporting episodes list preserves insertion order
    assert fact.supporting_episodes == ("episode-1", "episode-2", "episode-3")
    # Laplace confidence: (support+1)/(total_episodes+2) = (3+1)/(3+2) = 4/5 = 0.8
    assert abs(fact.confidence - 0.8) < 1e-9
    # Replay hash should be deterministic and non‑empty
    assert fact.replay_hash != ""


def test_deterministic_replay_of_facts():
    # Run two independent FactStores with identical episodes – they must end up identical.
    def run_store():
        s = FactStore()
        for i in range(1, 5):
            ep = make_simple_episode(eid=f"ep-{i}", tick=i)
            process_episode(ep, s)
        return s

    store_a = run_store()
    store_b = run_store()

    # Compare facts tuple‑by‑tuple
    assert store_a.facts == store_b.facts
    # Compare statistics
    assert store_a.mean_confidence() == store_b.mean_confidence()
    # Exact‑match lookup should be O(1) and return the fact
    key = ("causes", "apply_pressure", "bleeding_decrease")
    idx = store_a._index.get(key)  # internal, but deterministic
    assert idx is not None
    assert store_a.facts[idx].predicate == "causes"

    # Query API returns the same ordering
    q_a = store_a.query(predicate="causes")
    q_b = store_b.query(predicate="causes")
    assert q_a == q_b
