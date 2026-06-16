"""Deterministic tests for HomeostasisEngine.

The engine should raise compensation levels when stress exceeds the threshold.
"""

import pytest

from scrubin.systems.models import SystemsState, CardiovascularSystem, RespiratorySystem, RenalSystem, HepaticSystem, NeurologicSystem, EndocrineSystem, ImmuneSystem, MetabolicSystem
from scrubin.systems.homeostasis_engine import HomeostasisEngine


def _state_with_stress(stress: float) -> SystemsState:
    cv = CardiovascularSystem(stress_level=stress)
    resp = RespiratorySystem(stress_level=stress)
    renal = RenalSystem(stress_level=stress)
    hepatic = HepaticSystem(stress_level=stress)
    neuro = NeurologicSystem(stress_level=stress)
    endocrine = EndocrineSystem(stress_level=stress)
    immune = ImmuneSystem(stress_level=stress)
    metabolic = MetabolicSystem(stress_level=stress)
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


def test_compensation_increases_when_stress_high():
    state = _state_with_stress(0.6)
    new_state = HomeostasisEngine.evaluate(state)
    # All systems should have a higher compensation_level (default increment is 0.3).
    assert new_state.cardiovascular.compensation_level == pytest.approx(0.3)
    assert new_state.respiratory.compensation_level == pytest.approx(0.3)
    assert new_state.renal.compensation_level == pytest.approx(0.3)
    # Re‑evaluation must be deterministic.
    repeat = HomeostasisEngine.evaluate(state)
    assert new_state.deterministic_hash == repeat.deterministic_hash


def test_no_compensation_when_stress_below_threshold():
    state = _state_with_stress(0.4)
    new_state = HomeostasisEngine.evaluate(state)
    assert new_state.cardiovascular.compensation_level == 0.0
    assert new_state.metabolic.compensation_level == 0.0
