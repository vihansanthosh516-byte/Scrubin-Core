"""Tests for the deterministic ProceduralPhaseEngine.

These tests verify that phase predicates are respected and that the engine
produces reproducible ``WorldState`` transitions.
"""

from scrubin.world.state import WorldState, ProcedureState, TimelineEvent
from scrubin.engine.procedure import ProcedurePhase
from scrubin.engine.procedural_phase_engine import ProceduralPhaseEngine
from scrubin.engine.random import SimulationRNG
from scrubin.engine.constraints import Constraint


class AlwaysTrue(Constraint):
    def evaluate(self, world: WorldState) -> bool:
        return True


class AlwaysFalse(Constraint):
    def evaluate(self, world: WorldState) -> bool:
        return False


def test_no_transition_simple_phase():
    # Phase with no completion conditions – should never auto‑advance.
    phase = ProcedurePhase(
        id="phase1",
        title="Test Phase",
        entry_conditions=[],
        completion_conditions=[],
        failure_conditions=[],
    )
    world = WorldState(
        tick=1,
        seed=42,
        procedure=ProcedureState(current_phase="phase1"),
    )
    engine = ProceduralPhaseEngine(phases={"phase1": phase})
    rng = SimulationRNG(seed=42)
    new_world = engine.evaluate(world, rng)
    assert new_world.procedure.current_phase == "phase1"
    # No timeline events should be added.
    assert len(new_world.timeline) == 0


def test_failure_triggers_event():
    phase = ProcedurePhase(
        id="phase_fail",
        title="Fail Phase",
        entry_conditions=[],
        completion_conditions=[],
        failure_conditions=[AlwaysFalse()],  # always false -> no failure
    )
    # Use a failing condition that returns True.
    phase.failure_conditions.append(AlwaysTrue())
    world = WorldState(
        tick=5,
        seed=1,
        procedure=ProcedureState(current_phase="phase_fail"),
    )
    engine = ProceduralPhaseEngine(phases={"phase_fail": phase})
    rng = SimulationRNG(seed=1)
    new_world = engine.evaluate(world, rng)
    # Expect a failure event.
    assert any(e.description.startswith("phase_failed") for e in new_world.timeline)


def test_completion_and_next_phase():
    # Phase A completes and transitions to Phase B if entry conditions allow.
    phase_a = ProcedurePhase(
        id="A",
        title="Phase A",
        entry_conditions=[],
        completion_conditions=[AlwaysTrue()],
        failure_conditions=[],
        # Attach metadata to indicate the next phase.
        metadata={"next_phase": "B"},
    )
    phase_b = ProcedurePhase(
        id="B",
        title="Phase B",
        entry_conditions=[AlwaysTrue()],
        completion_conditions=[],
        failure_conditions=[],
    )
    world = WorldState(
        tick=10,
        seed=99,
        procedure=ProcedureState(current_phase="A"),
    )
    engine = ProceduralPhaseEngine(phases={"A": phase_a, "B": phase_b})
    rng = SimulationRNG(seed=99)
    new_world = engine.evaluate(world, rng)
    # Phase should have advanced to B.
    assert new_world.procedure.current_phase == "B"
    # Timeline should contain both completed and entered events.
    descriptions = [e.description for e in new_world.timeline]
    assert "phase_completed:A" in descriptions
    assert "phase_entered:B" in descriptions
