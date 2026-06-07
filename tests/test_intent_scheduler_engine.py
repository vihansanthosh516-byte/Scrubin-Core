# -*- coding: utf-8 -*-
"""Deterministic tests for IntentScheduler.

The scheduler should collect all pending intents from the IntentGraph and store
them in an ``IntentSchedule``. It also emits an ``intent_generated`` event when
there are executable intents.
"""

from scrubin.ontology.intent_scheduler import IntentScheduler
from scrubin.engine.random import SimulationRNG
from scrubin.world.state import WorldState
from scrubin.ontology.intent_graph import IntentGraph, IntentNode


def _run_scheduler(world: WorldState) -> WorldState:
    rng = SimulationRNG(seed=0)
    scheduler = IntentScheduler(rng)
    return scheduler.schedule(world)


def test_intent_scheduler_collects_pending_intents():
    # Create two pending intents.
    intent_a = IntentNode(intent_id="a")
    intent_b = IntentNode(intent_id="b")
    ig = IntentGraph().add_intent(intent_a).add_intent(intent_b)
    world = WorldState(tick=0, seed=0, intent_graph=ig)
    new_world = _run_scheduler(world)
    schedule = new_world.intent_schedule
    # Both intents should be executable (sorted by id).
    assert schedule.executable_intents == ("a", "b")
    # Verify timeline event.
    assert any(e.description == "intent_generated" for e in new_world.timeline)


def test_intent_scheduler_no_pending_intents():
    # Empty intent graph – scheduler should produce empty schedule and no event.
    world = WorldState(tick=0, seed=0)
    new_world = _run_scheduler(world)
    schedule = new_world.intent_schedule
    assert schedule.executable_intents == tuple()
    assert not any(e.description == "intent_generated" for e in new_world.timeline)
