"""Deterministic stabilization subsystem tests.

Ensures that the entire stabilization pipeline produces identical deterministic
hashes, correction plans, rollback selections and convergence reports across
repeated runs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import pytest

from scrubin.stabilization.stabilization_manager import StabilizationManager
from scrubin.stabilization.models import StabilityViolation
from scrubin.stabilization.correction_engine import CorrectionEngine
from scrubin.stabilization.rollback_engine import RollbackEngine
from scrubin.stabilization.convergence_engine import ConvergenceEngine

# ---------------------------------------------------------------------------
# Mock state used by StabilizationManager.tick
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class MockState:
    previous_deterministic_hash: int = 0
    deterministic_hash: int = 42
    simulation_snapshot: int = 1
    evaluation_snapshot: int = 2
    memory_snapshot: int = 3
    knowledge_snapshot: int = 4
    executive_snapshot: int = 5
    learning_snapshot: int = 6


def test_stabilization_deterministic_hash_replay():
    """Repeated manager ticks produce identical snapshot hashes."""
    state = MockState()
    snapshots = [StabilizationManager.tick(state) for _ in range(10)]
    hashes = [snap.deterministic_hash for snap in snapshots]
    assert len(set(hashes)) == 1, "Deterministic hashes differ across runs"


def test_rollback_deterministic_selection():
    """RollbackEngine selects the minimal hash deterministically."""
    state = MockState(deterministic_hash=7)
    stable_hashes = (10, 5, 20)
    rollback = RollbackEngine.evaluate(state, stable_hashes)
    assert rollback.required is True
    assert rollback.target_hash == 5


def test_correction_engine_ordering():
    """CorrectionEngine returns actions in deterministic order.

    The ordering is defined by the tuple sort key
    ``(target_component, action_type, parameters)``.
    """
    violations = (
        StabilityViolation(description="cognitive_contradiction", severity=0.3),
        StabilityViolation(description="structural_oscillation", severity=0.5),
        StabilityViolation(description="behavioral_divergence", severity=0.6),
        StabilityViolation(description="physiological_instability", severity=0.4),
    )
    plan = CorrectionEngine.generate(violations)
    # Expected ordering by target_component alphabetically.
    expected_targets = ["behaviour", "cognition", "physiology", "system"]
    actual_targets = [a.target_component for a in plan.actions]
    assert actual_targets == expected_targets
    # Deterministic hash must be stable across runs.
    h1 = plan.deterministic_hash
    h2 = CorrectionEngine.generate(violations).deterministic_hash
    assert h1 == h2


def test_convergence_engine_statuses():
    """ConvergenceEngine reports correct status for hash relationships."""
    # Fixed point
    report_fp = ConvergenceEngine.evaluate(1000, 1000)
    assert report_fp.status == "fixed_point"
    # Oscillation (small delta < 10)
    report_osc = ConvergenceEngine.evaluate(1000, 1005)
    assert report_osc.status == "oscillation"
    # Divergence (large delta)
    report_div = ConvergenceEngine.evaluate(1000, 1020)
    assert report_div.status == "divergence"
