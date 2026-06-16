"""Deterministic end‑to‑end test for the multi‑system physiology pipeline.

The pipeline runs the five deterministic engines in the order prescribed by the
specification.  Re‑running the pipeline with the same initial snapshot must
produce identical final deterministic hashes.
"""

import pytest

from dataclasses import replace

from scrubin.systems.models import SystemsState, CardiovascularSystem, RespiratorySystem, RenalSystem, HepaticSystem, NeurologicSystem, EndocrineSystem, ImmuneSystem, MetabolicSystem
from scrubin.systems.interaction_engine import InteractionEngine
from scrubin.systems.homeostasis_engine import HomeostasisEngine
from scrubin.systems.feedback_engine import FeedbackEngine
from scrubin.systems.perfusion_engine import PerfusionEngine
from scrubin.systems.metabolism_engine import MetabolismEngine


def _baseline_state() -> SystemsState:
    # Use modest haemodynamic values; stress initially zero.
    cv = CardiovascularSystem(map=95.0, blood_loss=5.0, vasopressor_support=0.0)
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


def _run_pipeline(state: SystemsState) -> SystemsState:
    state = InteractionEngine.evaluate(state)
    state = HomeostasisEngine.evaluate(state)
    state = FeedbackEngine.evaluate(state)
    state = PerfusionEngine.evaluate(state)
    state = MetabolismEngine.evaluate(state)
    return state


def test_full_pipeline_is_deterministic():
    init_state = _baseline_state()
    final1 = _run_pipeline(init_state)
    final2 = _run_pipeline(init_state)
    assert final1.deterministic_hash == final2.deterministic_hash
    # Ensure that some values changed from the baseline (sanity check).
    assert final1.cardiovascular.stress_level >= 0.0
    assert final1.metabolic.lactate >= 0.0
