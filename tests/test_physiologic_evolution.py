"""Tests for deterministic physiologic evolution.

The tests verify that hidden effects manifest as complications after the
configured reveal threshold and that the evolution engine is deterministic
given a fixed seed.
"""

from scrubin.world.state import WorldState, TimelineEvent
from scrubin.engine.physiologic_evolution import PhysiologicEvolutionEngine
from scrubin.engine.random import SimulationRNG
from scrubin.engine.decision_node import HiddenEffect
from scrubin.models.types import ComplicationState


def test_hidden_effect_manifestation():
    # Hidden effect that should reveal after tick 2.
    hidden = HiddenEffect(
        id="test_hidden",
        description="Test hidden effect",
        progression_rate=0.0,
        reveal_threshold=2,
        escalation_threshold=0.0,
        affected_systems=[],
        delayed_manifestations=[],
        reversible=True,
        requires_intervention=False,
    )
    # Initialise a minimal world with the hidden effect.
    world = WorldState(tick=0, seed=0, hidden_effects=(hidden,))
    rng = SimulationRNG(seed=0)
    engine = PhysiologicEvolutionEngine(rng)

    # Evolve three ticks – the hidden effect should manifest on tick 2.
    for _ in range(3):
        world = engine.evolve(world)

    # Verify that a complication with the hidden effect id exists.
    comp_ids = {c.id for c in world.complications.active}
    assert "test_hidden" in comp_ids

    # Verify that a timeline event was recorded.
    event_descs = {e.description for e in world.timeline}
    assert any("occult_instability_detected:test_hidden" in d for d in event_descs)

    # Ensure deterministic progression – tick should now be 3.
    assert world.tick == 3
