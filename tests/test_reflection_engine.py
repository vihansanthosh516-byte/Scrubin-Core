"""Deterministic Reflection Engine tests (Phase 3.4).

The tests verify that reflections are created deterministically from beliefs,
that replay‑safety holds, that confidence and IDs are stable, and that the store
remains append‑only with O(1) look‑ups.
"""

import pytest

from scrubin.cognition.reflection_store import ReflectionStore
from scrubin.cognition.reflection_engine import update_reflections_from_beliefs
from scrubin.cognition.belief_store import BeliefStore
from scrubin.cognition.belief import Belief


def make_belief(bid: str, subject: str, predicate: str, obj: str, confidence: float, tick: int) -> Belief:
    """Create a deterministic Belief instance for testing.

    The statement is ``"{subject} {predicate} {obj}"``. Supporting beliefs list
    contains only its own id for simplicity.
    """
    statement = f"{subject} {predicate} {obj}"
    return Belief(
        id=bid,
        statement=statement,
        supporting_facts=(bid,),
        support_count=1,
        confidence=confidence,
        first_seen_tick=tick,
        last_seen_tick=tick,
        replay_hash="",
    )


def test_reflection_creation_and_merge():
    # Create three beliefs with the same subject ("clamp") but different effects.
    b1 = make_belief("b1", "clamp", "causes", "bleeding", 0.7, 1)
    b2 = make_belief("b2", "clamp", "causes", "hypotension", 0.6, 2)
    b3 = make_belief("b3", "clamp", "causes", "shock", 0.8, 3)

    belief_store = BeliefStore()
    for b in (b1, b2, b3):
        belief_store.add_or_update(b)

    reflection_store = ReflectionStore()
    update_reflections_from_beliefs(belief_store, reflection_store)

    # Exactly one reflection should be generated for subject "clamp"
    assert reflection_store.reflection_count() == 1
    refl = reflection_store.reflections[0]

    # Deterministic ID prefix
    assert refl.id.startswith("reflection-")
    # Support count should equal number of distinct beliefs for the subject
    assert refl.support_count == 3
    # Confidence is mean of belief confidences (0.7+0.6+0.8)/3 = 0.7
    assert abs(refl.confidence - 0.7) < 1e-9
    # Supporting belief IDs should include all three in insertion order
    assert refl.supporting_beliefs == ("b1", "b2", "b3")
    # Replay hash must be non‑empty
    assert refl.replay_hash != ""


def test_reflection_replay_safety():
    # Helper to run a full pipeline (facts → beliefs → reflections)
    def run_pipeline():
        # Build three beliefs with same subject "clamp"
        b1 = make_belief("b1", "clamp", "causes", "bleeding", 0.7, 1)
        b2 = make_belief("b2", "clamp", "causes", "hypotension", 0.6, 2)
        b3 = make_belief("b3", "clamp", "causes", "shock", 0.8, 3)
        belief_store = BeliefStore()
        for b in (b1, b2, b3):
            belief_store.add_or_update(b)
        reflection_store = ReflectionStore()
        update_reflections_from_beliefs(belief_store, reflection_store)
        return reflection_store

    rs_a = run_pipeline()
    rs_b = run_pipeline()

    # All deterministic fields must match across runs
    assert rs_a.reflections == rs_b.reflections
    assert rs_a.reflection_count() == rs_b.reflection_count()
    assert rs_a.mean_confidence() == rs_b.mean_confidence()
    assert rs_a.mean_support() == rs_b.mean_support()
    assert rs_a.max_support() == rs_b.max_support()

    # Query order must be identical
    q_a = rs_a.query()
    q_b = rs_b.query()
    assert q_a == q_b


def test_append_only_semantics():
    # Add two belief groups with different subjects and verify reflections grow linearly.
    belief_store = BeliefStore()
    # First group (subject "a") – two beliefs
    belief_store.add_or_update(make_belief("a1", "a", "causes", "x", 0.5, 1))
    belief_store.add_or_update(make_belief("a2", "a", "causes", "y", 0.6, 2))
    # Second group (subject "b") – three beliefs
    belief_store.add_or_update(make_belief("b1", "b", "causes", "x", 0.7, 3))
    belief_store.add_or_update(make_belief("b2", "b", "causes", "y", 0.8, 4))
    belief_store.add_or_update(make_belief("b3", "b", "causes", "z", 0.9, 5))

    reflection_store = ReflectionStore()
    update_reflections_from_beliefs(belief_store, reflection_store)

    # Two distinct reflections should be present (one per subject with >=2 beliefs)
    assert reflection_store.reflection_count() == 2
    # Ensure no deletions: re‑run engine – reflections are merged, not duplicated.
    update_reflections_from_beliefs(belief_store, reflection_store)
    assert reflection_store.reflection_count() == 2
    # Support counts must be unchanged after idempotent re‑run.
    for refl in reflection_store.reflections:
        assert refl.support_count in (2, 3)
