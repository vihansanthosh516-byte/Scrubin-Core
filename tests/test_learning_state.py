import pytest
from dataclasses import FrozenInstanceError

from scrubin.cognition.learning_state import LearningObservation, LearningState, LearningPattern, Belief

# ---------------------------------------------------------------------------
# Immutability checks
# ---------------------------------------------------------------------------

def test_learning_observation_is_frozen():
    obs = LearningObservation(
        id="obs_1",
        tick=10,
        source_reflection_id="ref_1",
        category="energy",
        lesson="energy low",
        confidence=1.0,
        severity=0.5,
        tags=("low",),
    )
    with pytest.raises(FrozenInstanceError):
        # Attempt to mutate a frozen dataclass should raise.
        obs.tick = 99


def test_learning_state_is_frozen():
    state = LearningState()
    with pytest.raises(FrozenInstanceError):
        state.learning_tick = 5

# ---------------------------------------------------------------------------
# Duplicate observation handling
# ---------------------------------------------------------------------------

def test_duplicate_observations_are_ignored():
    obs1 = LearningObservation(
        id="obs_1",
        tick=1,
        source_reflection_id="ref_1",
        category="cat",
        lesson="lesson",
        confidence=1.0,
        severity=0.5,
        tags=(),
    )
    # Duplicate with same id
    obs2 = LearningObservation(
        id="obs_1",
        tick=2,
        source_reflection_id="ref_2",
        category="cat",
        lesson="lesson2",
        confidence=0.9,
        severity=0.4,
        tags=(),
    )
    state = LearningState().add_observation(obs1).add_observation(obs2)
    # Only one observation should be stored.
    assert len(state.observations) == 1
    assert state.observations[0].id == "obs_1"

# ---------------------------------------------------------------------------
# Deterministic ordering of observations
# ---------------------------------------------------------------------------

def test_observation_ordering_is_deterministic():
    # Two observations with different ticks and ids added in reverse order.
    obs_a = LearningObservation(
        id="a",
        tick=5,
        source_reflection_id="ref_a",
        category="cat",
        lesson="lesson",
        confidence=1.0,
        severity=0.5,
        tags=(),
    )
    obs_b = LearningObservation(
        id="b",
        tick=3,
        source_reflection_id="ref_b",
        category="cat",
        lesson="lesson",
        confidence=1.0,
        severity=0.5,
        tags=(),
    )
    # Add in reverse chronological order.
    state = LearningState().add_observation(obs_a).add_observation(obs_b)
    # Expected order: first by tick (ascending) then by id.
    assert state.observations[0].id == "b"
    assert state.observations[1].id == "a"

# ---------------------------------------------------------------------------
# Learning tick updates
# ---------------------------------------------------------------------------

def test_learning_tick_update():
    state = LearningState().with_learning_tick(42)
    assert state.learning_tick == 42
