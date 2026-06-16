"""Deterministic tests for the InteractionEngine.

The tests verify that organ‑system interactions produce the expected deterministic
updates and that repeated evaluations yield identical hashes.
"""

import pytest

from scrubin.systems.models import (
    SystemsState,
    CardiovascularSystem,
    RespiratorySystem,
    RenalSystem,
    HepaticSystem,
    NeurologicSystem,
    EndocrineSystem,
    ImmuneSystem,
    MetabolicSystem,
)
from scrubin.systems.interaction_engine import InteractionEngine


def _default_state(cv_perf: float = 1.0) -> SystemsState:
    cv = CardiovascularSystem(perfusion=cv_perf)
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


def test_cardiovascular_affects_renal_and_metabolic():
    # Low perfusion in the heart should proportionally lower renal perfusion and raise metabolic stress.
    state = _default_state(cv_perf=0.3)
    new_state = InteractionEngine.evaluate(state)
    # Renal perfusion is scaled by CV perfusion (initial renal perfusion = 1.0).
    assert new_state.renal.perfusion == pytest.approx(0.3)
    # Metabolic stress should increase because renal perfusion is below 0.5.
    assert new_state.metabolic.stress_level > 0.0
    # Deterministic hash stability – two identical evaluations give the same hash.
    repeat = InteractionEngine.evaluate(state)
    assert new_state.deterministic_hash == repeat.deterministic_hash
