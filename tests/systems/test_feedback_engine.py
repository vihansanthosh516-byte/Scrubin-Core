"""Deterministic tests for FeedbackEngine.

Positive feedback (metabolic stress → cardiovascular failure) and the resulting
negative feedback (heart failure → stress increase across all systems) are
checked for deterministic behaviour.
"""

import pytest

from scrubin.systems.models import SystemsState, CardiovascularSystem, RespiratorySystem, RenalSystem, HepaticSystem, NeurologicSystem, EndocrineSystem, ImmuneSystem, MetabolicSystem
from scrubin.systems.feedback_engine import FeedbackEngine


def _baseline_state() -> SystemsState:
    cv = CardiovascularSystem()
    resp = RespiratorySystem()
    renal = RenalSystem()
    hepatic = HepaticSystem()
    neuro = NeurologicSystem()
    endocrine = EndocrineSystem()
    immune = ImmuneSystem()
    metabolic = MetabolicSystem()
    return SystemsState(
        cardiovascular=cv,
        respiratory=resp,
        renal=renal,
        hepatic=hepatic,
        neurologic=neuro,
        endocrine=endocrine,
        immune=immune,
        metabolic=metabolic,
    )


def test_metabolic_stress_triggers_cardiovascular_failure():
    state = _baseline_state()
    # Inject high metabolic stress.
    metabolic = state.metabolic.replace(stress_level=6.0) if hasattr(state.metabolic, "replace") else state.metabolic
    # Simpler: use replace from dataclasses.
    from dataclasses import replace as dc_replace
    metabolic = dc_replace(state.metabolic, stress_level=6.0)
    state = dc_replace(state, metabolic=metabolic)
    new_state = FeedbackEngine.evaluate(state)
    assert new_state.cardiovascular.failure_state is True
    # Re‑evaluation should keep the failure state and add deterministic stress.
    newer = FeedbackEngine.evaluate(new_state)
    assert newer.cardiovascular.stress_level > new_state.cardiovascular.stress_level
    # Deterministic hash stability.
    assert newer.deterministic_hash == FeedbackEngine.evaluate(new_state).deterministic_hash
