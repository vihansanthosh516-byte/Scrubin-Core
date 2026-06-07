# -*- coding: utf-8 -*-
"""Deterministic replay‑safety tests for ExecutivePlanner.

These tests ensure that:
* Running the planner on the same ``WorldState`` with the same RNG seed
  always produces the same result (identical world, identical timeline).
* The planner does **not** mutate the input ``WorldState`` (immutability).
* Timeline events are emitted exactly once when a new intent is created
  and never on subsequent identical invocations.
"""

from scrubin.ontology.executive_planner import ExecutivePlanner
from scrubin.engine.random import SimulationRNG
from scrubin.world.state import WorldState


def _run_once(world: WorldState) -> WorldState:
    rng = SimulationRNG(seed=0)
    planner = ExecutivePlanner(rng)
    return planner.plan(world)


def test_executive_planner_idempotent_replay():
    # Start from a clean world (no intent graph).
    base = WorldState(tick=0, seed=0)
    first = _run_once(base)
    second = _run_once(base)

    # The planner should produce identical worlds (including timeline).
    assert first == second
    # Exactly one timeline event should be present (root intent creation).
    assert len(first.timeline) == 1
    assert first.timeline[0].description == "intent_generated"

    # The original world must remain unchanged – ``WorldState`` is frozen.
    assert base.intent_graph.intents == ()
    assert base.timeline == ()


def test_executive_planner_no_new_intent_on_subsequent_runs():
    # Run once to create the root intent.
    base = WorldState(tick=0, seed=0)
    first = _run_once(base)
    # Run again on the world that already contains the root intent.
    second = _run_once(first)

    # No additional events should be added; worlds should be equal.
    assert first == second
    assert len(second.timeline) == 1  # still only the original creation event
    # Ensure the intent graph still contains exactly one intent.
    assert len(second.intent_graph.intents) == 1
    assert second.intent_graph.intents[0].intent_id == "root_intent"
