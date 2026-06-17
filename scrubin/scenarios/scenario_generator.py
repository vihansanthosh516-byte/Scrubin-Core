"""Deterministic scenario generator combining all sub‑engines.
"""

from __future__ import annotations

from ..systems.models import SystemsState
from ..simulation.models import EnvironmentState, SimulationWorld
from .seed_engine import ScenarioSeedEngine
from .stress_engine import StressInjectionEngine
from .adversarial_engine import AdversarialScenarioEngine
from .failure_mode_engine import FailureModeEngine
from .models import ScenarioProfile, ScenarioSnapshot


class ScenarioGenerator:
    """Combine seed, stress, adversarial conditions, and failure modes.

    The resulting ``ScenarioProfile`` is fully deterministic for a given set of
    inputs.
    """

    @staticmethod
    def generate(procedure_id: str, anatomy_complexity: int, physiology: SystemsState, environment: EnvironmentState) -> ScenarioProfile:
        seed = ScenarioSeedEngine.generate(procedure_id, anatomy_complexity, physiology, environment)
        stresses = StressInjectionEngine.inject(seed)
        adv = AdversarialScenarioEngine.generate(seed, stresses)
        failures = FailureModeEngine.map_conditions(adv)
        return ScenarioProfile(seed=seed, stress_vectors=stresses, adversarial_conditions=adv, failure_modes=failures)
