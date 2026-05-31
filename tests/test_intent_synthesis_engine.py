'''Tests for the IntentSynthesisEngine.

These tests ensure that the engine:
* generates an ``AutonomousIntent`` with the proper ``id`` field,
* updates the ``IntentiveCognitionState`` with the current ``cognitive_tick``,
* records deterministic timeline events, and
* selects the dominant intent according to the specification.
'''

from scrubin.cognition.intent_synthesis_engine import IntentSynthesisEngine
from scrubin.engine.random import SimulationRNG
from scrubin.world.state import WorldState


def _run_engine(ticks: int) -> WorldState:
    rng = SimulationRNG(seed=0)
    engine = IntentSynthesisEngine(rng)
    world = WorldState(tick=0, seed=0)
    for _ in range(ticks):
        world = engine.evolve(world)
        # Advance the world tick to ensure distinct intent IDs per tick
        world = world.with_tick(world.tick + 1)
    return world


def test_intent_synthesis_creates_intent_and_updates_tick():
    world = _run_engine(1)
    ics = world.intentive_cognition_state
    # Exactly one autonomous intent should exist
    assert len(ics.active_intents) == 1
    # The cognitive_tick stored in the state must equal the world tick (still 0)
    assert ics.cognitive_tick == world.tick - 1
    # Timeline must contain the creation event
    assert any('autonomous_intent_created' in ev.description for ev in world.timeline)
    # Dominant intent id should match the created intent id
    assert ics.dominant_intent_id == ics.active_intents[0].id


def test_intent_synthesis_dominant_intent_selection_ordering():
    # Run two ticks – we will have two intents with deterministic ids
    world = _run_engine(2)
    ics = world.intentive_cognition_state
    assert len(ics.active_intents) == 2
    # Confidence alternates: tick 0 -> 0.6, tick 1 -> 0.8, so later intent dominates
    assert ics.dominant_intent.id == "auto_intent_1"
    # Ensure the dominant_intent_shifted event was emitted on the second tick
    shift_events = [ev for ev in world.timeline if 'dominant_intent_shifted' in ev.description]
    assert any("dominant_intent_shifted:auto_intent_1" in ev.description for ev in shift_events)
