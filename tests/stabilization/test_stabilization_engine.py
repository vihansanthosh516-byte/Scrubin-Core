"""Deterministic stabilization engine tests (Phase 8.6)."""

from scrubin.stabilization.models import DriftVector, SystemStabilityState, StabilityViolation, CorrectionPlan, RollbackState, ConvergenceReport, StabilizationSnapshot
from scrubin.stabilization.drift_engine import DriftEngine
from scrubin.stabilization.stability_engine import StabilityEngine
from scrubin.stabilization.correction_engine import CorrectionEngine
from scrubin.stabilization.rollback_engine import RollbackEngine
from scrubin.stabilization.convergence_engine import ConvergenceEngine
from scrubin.stabilization.stabilization_manager import StabilizationManager

# Simple mock state container with deterministic_hash attributes.
class MockState:
    def __init__(self, **hashes):
        self.__dict__.update(hashes)
        self.deterministic_hash = sum(hashes.values())
        self.previous_deterministic_hash = self.deterministic_hash - 1

    # For rollback evaluation we provide a list of stable hashes.
    @property
    def stable_hashes(self):
        return (0, 1, 2)


def test_drift_determinism():
    state = MockState(simulation_snapshot=100, evaluation_snapshot=105, memory_snapshot=110, knowledge_snapshot=115, executive_snapshot=120, learning_snapshot=125)
    drift1 = DriftEngine.compute(state)
    drift2 = DriftEngine.compute(state)
    assert drift1.deterministic_hash == drift2.deterministic_hash

def test_stability_detection():
    # Force high drift values.
    drift = DriftVector(0.3, 0.3, 0.3, 0.3)
    stability = StabilityEngine.assess(drift)
    assert stability.stability_score < 1.0
    assert len(stability.violations) == 4
    # Deterministic ordering of violations.
    descriptions = [v.description for v in stability.violations]
    assert descriptions == sorted(descriptions)

def test_correction_determinism():
    violations = (
        StabilityViolation(description="behavioral_divergence", severity=0.3),
        StabilityViolation(description="structural_oscillation", severity=0.3),
    )
    plan1 = CorrectionEngine.generate(violations)
    plan2 = CorrectionEngine.generate(violations)
    assert plan1.deterministic_hash == plan2.deterministic_hash
    # Actions are sorted deterministically.
    actions = [a.action_type for a in plan1.actions]
    assert actions == sorted(actions)

def test_rollback_consistency():
    state = MockState(simulation_snapshot=5)
    rollback = RollbackEngine.evaluate(state, stable_hashes=(1, 2, 3))
    assert rollback.required is True
    assert rollback.target_hash == 1

def test_convergence_reports():
    report_fp = ConvergenceEngine.evaluate(10, 10)
    report_os = ConvergenceEngine.evaluate(10, 15)
    report_div = ConvergenceEngine.evaluate(10, 30)
    assert report_fp.status == "fixed_point"
    assert report_os.status == "oscillation"
    assert report_div.status == "divergence"

def test_full_pipeline_determinism():
    state = MockState(simulation_snapshot=100, evaluation_snapshot=100, memory_snapshot=100, knowledge_snapshot=100, executive_snapshot=100, learning_snapshot=100)
    snap1 = StabilizationManager.tick(state, stable_hashes=(0, 1, 2))
    snap2 = StabilizationManager.tick(state, stable_hashes=(0, 1, 2))
    assert snap1.deterministic_hash == snap2.deterministic_hash

def test_no_state_mutation():
    state = MockState(simulation_snapshot=100)
    _ = StabilizationManager.tick(state)
    # Ensure original attributes unchanged.
    assert state.simulation_snapshot == 100
    assert hasattr(state, "deterministic_hash")
