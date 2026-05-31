import pytest

from scrubin.cognition.meta_learning_engine import MetaLearningEngine
from scrubin.cognition.reflection_state import ReflectionState, DecisionReflection
from scrubin.world.state import WorldState


def _make_reflection(id_suffix: str, tick: int, outcome: str = "success") -> DecisionReflection:
    return DecisionReflection(
        id=f"ref_{id_suffix}",
        tick=tick,
        goal_id=None,
        intent_id=None,
        conflict_id=None,
        outcome=outcome,
        reason_tags=("tag",),
        confidence=1.0,
        stability_score=1.0,
    )


def test_meta_learning_engine_creates_observations_and_events():
    # Build a world with two distinct reflections.
    refl1 = _make_reflection("a", 5, outcome="success")
    refl2 = _make_reflection("b", 10, outcome="arbitrated")
    refl_state = ReflectionState().add_reflection(refl1).add_reflection(refl2)
    world = WorldState(tick=20, reflection_state=refl_state)

    engine = MetaLearningEngine(rng=None)
    new_world = engine.evolve(world)

    # Verify that two LearningObservations have been added.
    obs = new_world.learning_state.observations
    assert len(obs) == 2
    # Deterministic IDs: "learn_{reflection.id}".
    ids = {o.id for o in obs}
    assert "learn_ref_a" in ids
    assert "learn_ref_b" in ids

    # Verify that timeline events were emitted for each observation and tick update.
    event_descs = {e.description for e in new_world.timeline}
    assert "learning_observation_created:learn_ref_a" in event_descs
    assert "learning_observation_created:learn_ref_b" in event_descs
    assert "learning_tick_updated:20" in event_descs

    # Verify deterministic ordering – observations sorted by tick then id.
    sorted_obs = sorted(obs, key=lambda o: (o.tick, o.id))
    assert list(obs) == sorted_obs
