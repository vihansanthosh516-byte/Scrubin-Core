"""Deterministic tests for MetabolismEngine.

The engine updates oxygen consumption, lactate and acidosis based on metabolic
stress using simple linear relationships.  Deterministic hash stability is also
checked.
"""

import pytest

from dataclasses import replace

from scrubin.systems.models import SystemsState, CardiovascularSystem, RespiratorySystem, RenalSystem, HepaticSystem, NeurologicSystem, EndocrineSystem, ImmuneSystem, MetabolicSystem
from scrubin.systems.metabolism_engine import MetabolismEngine


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


def test_metabolism_updates_based_on_stress():
    state = _baseline_state()
    # Inject metabolic stress = 2.0
    metabolic = replace(state.metabolic, stress_level=2.0)
    state = replace(state, metabolic=metabolic)
    new_state = MetabolismEngine.evaluate(state)
    expected_oxygen = state.metabolic.oxygen_consumption + 2.0 * 0.05
    expected_lactate = state.metabolic.lactate + 2.0 * 0.1
    expected_acidosis = state.metabolic.acidosis + 2.0 * 0.02
    assert new_state.metabolic.oxygen_consumption == pytest.approx(expected_oxygen)
    assert new_state.metabolic.lactate == pytest.approx(expected_lactate)
    assert new_state.metabolic.acidosis == pytest.approx(expected_acidosis)
    # Deterministic hash repeatability.
    repeat = MetabolismEngine.evaluate(state)
    assert new_state.deterministic_hash == repeat.deterministic_hash
