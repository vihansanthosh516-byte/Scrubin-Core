# -*- coding: utf-8 -*-
"""Deterministic tests for RecoveryEngine.

The engine should activate the salvage protocol when overload level >= 0.5 and emit a
'salvage_protocol_activated' event. Below the threshold it should keep the protocol
inactive and emit no events.
"""

from scrubin.ontology.recovery_engine import RecoveryEngine
from scrubin.engine.random import SimulationRNG
from scrubin.world.state import WorldState
from scrubin.ontology.overload_state import OverloadState


def _run_engine(world: WorldState) -> WorldState:
    rng = SimulationRNG(seed=0)
    engine = RecoveryEngine(rng)
    return engine.recover(world)


def test_recovery_engine_no_activation():
    # Overload level below threshold.
    world = WorldState(tick=0, seed=0, overload_state=OverloadState(overload_level=0.3))
    result = _run_engine(world)
    assert result.recovery_state.salvage_active is False
    assert not any(e.description == 'salvage_protocol_activated' for e in result.timeline)


def test_recovery_engine_activation():
    # Overload level above threshold.
    world = WorldState(tick=5, seed=0, overload_state=OverloadState(overload_level=0.6))
    result = _run_engine(world)
    assert result.recovery_state.salvage_active is True
    assert any(e.description == 'salvage_protocol_activated' and e.tick == world.tick for e in result.timeline)
