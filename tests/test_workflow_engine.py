# -*- coding: utf-8 -*-
"""Deterministic tests for WorkflowEngine.

The engine should select the first pending intent (sorted by id) as the current
maneuver and emit a ``workflow_progression`` event. When no pending intents exist it
should emit ``workflow_stalled`` and leave the maneuver empty.
"""

from scrubin.execution.workflow_engine import WorkflowEngine
from scrubin.engine.random import SimulationRNG
from scrubin.world.state import WorldState
from scrubin.ontology.intent_graph import IntentGraph, IntentNode


def _run_engine(world: WorldState) -> WorldState:
    rng = SimulationRNG(seed=0)
    engine = WorkflowEngine(rng)
    return engine.process(world)


def test_workflow_engine_progression():
    # Two pending intents – the engine should pick the first (sorted by id).
    intent_a = IntentNode(intent_id='a')
    intent_b = IntentNode(intent_id='b')
    ig = IntentGraph().add_intent(intent_a).add_intent(intent_b)
    world = WorldState(tick=0, seed=0, intent_graph=ig)
    new_world = _run_engine(world)
    tech = new_world.technical_execution_state
    assert tech.current_maneuver == 'a'
    assert any(e.description == 'workflow_progression:a' for e in new_world.timeline)


def test_workflow_engine_stalled():
    # Empty intent graph – should emit stalled event and keep maneuver empty.
    world = WorldState(tick=0, seed=0)
    new_world = _run_engine(world)
    tech = new_world.technical_execution_state
    assert tech.current_maneuver == ''
    assert any(e.description == 'workflow_stalled' for e in new_world.timeline)
