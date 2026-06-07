# -*- coding: utf-8 -*-
"""Deterministic replay‑safety tests for IntentScheduler.

The scheduler should produce the same ``WorldState`` (including timeline) when
run multiple times on identical input, and it must never mutate the original
state because ``WorldState`` is frozen.
"""

from scrubin.ontology.intent_scheduler import IntentScheduler
from scrubin.engine.random import SimulationRNG
from scrubin.world.state import WorldState
from scrubin.ontology.intent_graph import IntentGraph, IntentNode


def _run_once(world: WorldState) -> WorldState:
    rng = SimulationRNG(seed=0)
    scheduler = IntentScheduler(rng)
    return scheduler.schedule(world)


def test_intent_scheduler_deterministic_replay():
    # Build a world with two pending intents.
    ig = IntentGraph().add_intent(IntentNode(intent_id="a")).add_intent(IntentNode(intent_id="b"))
    base = WorldState(tick=0, seed=0, intent_graph=ig)
    first = _run_once(base)
    second = _run_once(base)

    # The scheduler must be deterministic – worlds are equal.
    assert first == second
    # One timeline event (intent_generated) should be present.
    assert len(first.timeline) == 1
    assert first.timeline[0].description == "intent_generated"
    # The schedule should list both intents in sorted order.
    assert first.intent_schedule.executable_intents == ("a", "b")

    # Original world must be unchanged.
    assert base.intent_schedule.executable_intents == ()
    assert base.timeline == ()


def test_intent_scheduler_no_events_on_empty_graph():
    base = WorldState(tick=0, seed=0)
    result = _run_once(base)
    # No intents → empty schedule, no timeline events.
    assert result.intent_schedule.executable_intents == ()
    assert result.timeline == ()
