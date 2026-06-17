"""Tests for Phase 8.7 deterministic global orchestrator.
The suite checks that identical inputs produce identical orchestration snapshots,
that the execution plan follows the required fixed order, and that replay
verification succeeds.
"""

from __future__ import annotations

import pytest
from dataclasses import FrozenInstanceError, dataclass

from scrubin.orchestration import GlobalOrchestrator

# Simple frozen dummy snapshot used across all subsystem arguments.
@dataclass(frozen=True, slots=True)
class DummySnapshot:
    name: str
    tick: int = 0

    @property
    def deterministic_hash(self) -> int:
        # Deterministic hash based on name and tick.
        return hash((self.name, self.tick))


def make_dummy(name: str) -> DummySnapshot:
    return DummySnapshot(name=name, tick=1)


def test_deterministic_tick_and_hash_stability():
    # Prepare a full set of dummy snapshots.
    snapshots = {
        "learning_snapshot": make_dummy("learning"),
        "adaptive_snapshot": make_dummy("adaptive"),
        "meta_snapshot": make_dummy("meta"),
        "simulation_snapshot": make_dummy("simulation"),
        "scenario_snapshot": make_dummy("scenario"),
        "evaluation_snapshot": make_dummy("evaluation"),
        "stabilization_snapshot": make_dummy("stabilization"),
    }

    orchestrator = GlobalOrchestrator()
    # Run first tick.
    orchestrator1 = orchestrator.run_tick(**snapshots)
    assert len(orchestrator1.history) == 1
    snap1 = orchestrator1.history[0]

    # Run a second tick with the same inputs – deterministic hash must match.
    orchestrator2 = orchestrator1.run_tick(**snapshots)
    assert len(orchestrator2.history) == 2
    snap2 = orchestrator2.history[-1]

    assert snap1.deterministic_hash == snap2.deterministic_hash
    # Execution plan order must be fixed.
    expected_order = ("scenario", "simulation", "meta", "learning", "adaptive", "evaluation", "stabilization")
    assert snap1.execution_plan.steps[0].name == expected_order[0]
    assert tuple(step.name for step in snap1.execution_plan.steps) == expected_order
    assert snap1.execution_trace.step_names == expected_order

    # Integration report should have no issues.
    assert snap1.integration_report.issues == ()
    # Replay verification must pass.
    assert snap1.replay_verification.verification_passed is True

    # Ensure that dummy snapshots are immutable.
    with pytest.raises(FrozenInstanceError):
        snapshots["learning_snapshot"].tick = 2


def test_run_simulation_and_replay_verification():
    # Factory that returns identical dummy snapshots for each tick.
    def factory(_tick_idx: int) -> dict:
        return {
            "learning_snapshot": make_dummy("learning"),
            "adaptive_snapshot": make_dummy("adaptive"),
            "meta_snapshot": make_dummy("meta"),
            "simulation_snapshot": make_dummy("simulation"),
            "scenario_snapshot": make_dummy("scenario"),
            "evaluation_snapshot": make_dummy("evaluation"),
            "stabilization_snapshot": make_dummy("stabilization"),
        }

    orchestrator = GlobalOrchestrator()
    orchestrator = orchestrator.run_simulation(ticks=3, snapshot_factory=factory)
    assert len(orchestrator.history) == 3
    # All snapshots must share the same deterministic hash due to identical inputs.
    hashes = [s.deterministic_hash for s in orchestrator.history]
    assert len(set(hashes)) == 1
    # Global replay verification across history should succeed.
    assert orchestrator.verify_replay()
