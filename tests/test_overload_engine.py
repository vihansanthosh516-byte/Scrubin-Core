# -*- coding: utf-8 -*-
"""Deterministic tests for OverloadEngine.

The engine should:
* Decay overload level when load is below threshold (no events).
* Increase overload level and emit overload_escalation when load exceeds the threshold.
"""

from scrubin.cognition.overload_engine import OverloadEngine
from scrubin.engine.random import SimulationRNG
from scrubin.world.state import WorldState
from scrubin.ontology.attention_state import AttentionState
from scrubin.ontology.overload_state import OverloadState

def _run_engine(world: WorldState) -> WorldState:
    rng = SimulationRNG(seed=0)
    engine = OverloadEngine(rng)
    return engine.evolve(world)

def test_overload_engine_no_escalation():
    base = WorldState(tick=0, seed=0)
    result = _run_engine(base)
    assert result.overload_state.overload_level == 0.0
    assert result.overload_state.overload_ticks == 0
    assert not any(e.description.startswith('overload_escalation') for e in result.timeline)

def test_overload_engine_escalation():
    att = AttentionState(current_load=15, overload_threshold=10)
    world = WorldState(tick=5, seed=0, attention_state=att, overload_state=OverloadState())
    result = _run_engine(world)
    assert result.overload_state.overload_level == 0.1
    assert result.overload_state.overload_ticks == 1
    assert any(e.description == 'overload_escalation' and e.tick == world.tick for e in result.timeline)
