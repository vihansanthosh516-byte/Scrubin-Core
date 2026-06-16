"""Deterministic tests for PerfusionEngine.

The engine computes a scaling factor from cardiovascular haemodynamics and
applies it to organ perfusion values.
"""

import pytest

from dataclasses import replace

from scrubin.systems.models import SystemsState, CardiovascularSystem, RenalSystem, HepaticSystem, NeurologicSystem, RespiratorySystem, EndocrineSystem, ImmuneSystem, MetabolicSystem
from scrubin.systems.perfusion_engine import PerfusionEngine


def _state_with_cv(map_val: float, blood_loss: float, vasopressor: float) -> SystemsState:
    cv = CardiovascularSystem(map=map_val, blood_loss=blood_loss, vasopressor_support=vasopressor)
    # Other systems start with default perfusion = 1.0.
    renal = RenalSystem()
    hepatic = HepaticSystem()
    neuro = NeurologicSystem()
    resp = RespiratorySystem()
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


def test_perfusion_scaling_factor_applied():
    # Parameters chosen to generate a deterministic factor.
    state = _state_with_cv(map_val=80.0, blood_loss=10.0, vasopressor=0.2)
    new_state = PerfusionEngine.evaluate(state)
    # Expected deterministic factor.
    cv = state.cardiovascular
    factor = (cv.map / 100.0) * (1.0 - cv.blood_loss * 0.001) * (1.0 + cv.vasopressor_support * 0.1)
    factor = max(0.0, min(2.0, factor))
    assert new_state.renal.perfusion == pytest.approx(state.renal.perfusion * factor)
    assert new_state.hepatic.perfusion == pytest.approx(state.hepatic.perfusion * factor)
    assert new_state.neurologic.perfusion == pytest.approx(state.neurologic.perfusion * factor)
    # Deterministic hash repeatability.
    repeat = PerfusionEngine.evaluate(state)
    assert new_state.deterministic_hash == repeat.deterministic_hash
