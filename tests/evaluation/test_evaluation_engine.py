"""Tests for Phase 8.5 deterministic evaluation pipeline.
The tests verify that identical inputs produce identical evaluation snapshots,
that correction proposals are generated deterministically, and that basic
issue detection works for missing subsystem snapshots.
"""

from __future__ import annotations

import types

import pytest

# Helper to construct a minimal snapshot object with a deterministic_hash and optional tick
def make_dummy(name: str, tick: int = 0) -> Any:
    class Dummy:
        def __init__(self, v: str, t: int):
            self._value = v
            self.tick = t
        @property
        def deterministic_hash(self) -> int:
            # Simple deterministic hash based on the name and tick
            return hash((self._value, self.tick))
        def __repr__(self):
            return f"Dummy({self._value!r}, tick={self.tick})"
    return Dummy(name, tick)


@pytest.fixture
def dummy_snapshots():
    # Create a set of dummy snapshots – knowledge_snapshot is intentionally omitted
    exec_snap = make_dummy("executive", tick=1)
    phys_snap = make_dummy("physiology", tick=1)
    mem_snap = make_dummy("memory", tick=1)
    learn_snap = make_dummy("learning", tick=1)
    sim_snap = make_dummy("simulation", tick=1)
    stab_snap = make_dummy("stabilization", tick=1)
    return dict(
        executive_snapshot=exec_snap,
        physiology_snapshot=phys_snap,
        knowledge_snapshot=None,  # trigger missing layer detection
        memory_snapshot=mem_snap,
        learning_snapshot=learn_snap,
        simulation_snapshot=sim_snap,
        stabilization_snapshot=stab_snap,
        executive_goals=(),
        executive_decisions=(),
        outcome_forecasts=(),
        risk_assessments=(),
    )


def test_evaluation_snapshot_deterministic_hash(dummy_snapshots):
    from scrubin.evaluation import EvaluationManager

    manager = EvaluationManager()
    snap1 = manager.evaluate(**dummy_snapshots)
    snap2 = manager.evaluate(**dummy_snapshots)

    # Deterministic hash must be identical across runs with identical inputs
    assert snap1.deterministic_hash == snap2.deterministic_hash

    # The health report must contain a missing_layers issue for knowledge
    assert any("knowledge" in issue for issue in snap1.health_report.issues)

    # CorrectionSet should contain a proposal addressing that issue and be sorted
    proposals = snap1.correction_set.proposals
    assert len(proposals) > 0
    # All proposals must be sorted by description then action
    sorted_proposals = tuple(sorted(proposals, key=lambda p: (p.description, p.action)))
    assert proposals == sorted_proposals

    # Ensure that reports are immutable – attempting to modify raises FrozenInstanceError
    from dataclasses import FrozenInstanceError
    with pytest.raises(FrozenInstanceError):
        snap1.health_report.issues = ("new_issue",)

    with pytest.raises(FrozenInstanceError):
        snap1.correction_set.proposals = ()


def test_decision_quality_metrics_are_deterministic():
    from scrubin.evaluation import EvaluationManager
    manager = EvaluationManager()
    # Provide simple deterministic decisions and goals
    Goal = types.SimpleNamespace  # lightweight placeholder with no attributes needed
    Decision = types.SimpleNamespace
    goals = (Goal(id="g1"), Goal(id="g2"))
    decisions = (
        Decision(id="d1", confidence=0.8, delayed=False),
        Decision(id="d2", confidence=0.5, delayed=True),
    )
    forecasts = (object(), object())
    risks = (object(),)
    snap = manager.evaluate(
        executive_snapshot=make_dummy("exec"),
        physiology_snapshot=make_dummy("phys"),
        knowledge_snapshot=make_dummy("know"),
        memory_snapshot=make_dummy("mem"),
        learning_snapshot=make_dummy("learn"),
        simulation_snapshot=make_dummy("sim"),
        stabilization_snapshot=make_dummy("stab"),
        executive_goals=goals,
        executive_decisions=decisions,
        outcome_forecasts=forecasts,
        risk_assessments=risks,
    )
    dq = snap.decision_quality_report
    # With two goals and two decisions, optimality should be 1.0
    assert dq.optimality == pytest.approx(1.0)
    # Efficiency should be forecasts per decision (2/2 = 1)
    assert dq.efficiency == pytest.approx(1.0)
    # There should be one delayed action
    assert dq.delayed_actions == 1
    # Confidence alignment average
    expected_conf = (0.8 + 0.5) / 2
    assert dq.confidence_alignment == pytest.approx(expected_conf)
