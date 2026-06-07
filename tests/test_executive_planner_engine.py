# -*- coding: utf-8 -*-
"""Deterministic tests for ExecutivePlanner.

The planner should create a root intent when the intent graph is empty and emit an
``intent_generated`` event. When a graph already contains intents it should be a
no‑op.
"""

from scrubin.ontology.executive_planner import ExecutivePlanner
from scrubin.engine.random import SimulationRNG
from scrubin.world.state import WorldState
from scrubin.ontology.intent_graph import IntentGraph


def _run_planner(world: WorldState) -> WorldState:
    rng = SimulationRNG(seed=0)
    planner = ExecutivePlanner(rng)
    return planner.plan(world)


def test_executive_planner_creates_root_intent():
    # Start with an empty world (no intent graph).
    world = WorldState(tick=0, seed=0)
    new_world = _run_planner(world)
    # Expect a single root intent.
    assert len(new_world.intent_graph.intents) == 1
    root_intent = new_world.intent_graph.intents[0]
    assert root_intent.intent_id == "root_intent"
    # Verify timeline event.
    assert any(e.description == "intent_generated" for e in new_world.timeline)


def test_executive_planner_idempotent_when_intents_exist():
    # Build a world with a pre‑existing intent.
    from scrubin.ontology.intent_graph import IntentNode
    ig = IntentGraph().add_intent(IntentNode(intent_id="existing"))
    world = WorldState(tick=1, seed=0, intent_graph=ig)
    new_world = _run_planner(world)
    # Should retain the existing intent and not add a root.
    assert len(new_world.intent_graph.intents) == 1
    assert new_world.intent_graph.intents[0].intent_id == "existing"
    assert not any(e.description == "intent_generated" for e in new_world.timeline)
