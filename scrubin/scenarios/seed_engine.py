"""Deterministic scenario seed generation engine.

The seed is derived purely from deterministic inputs using built‑in hash.
"""

from __future__ import annotations

from ..systems.models import SystemsState
from ..simulation.models import EnvironmentState
from .models import ScenarioSeed


class ScenarioSeedEngine:
    """Generate a deterministic ``ScenarioSeed``.

    Parameters:
    * ``procedure_id`` – identifier string for the surgical procedure.
    * ``anatomy_complexity`` – integer level of anatomical difficulty.
    * ``physiology`` – a ``SystemsState`` instance.
    * ``environment`` – an ``EnvironmentState`` instance.
    """

    @staticmethod
    def generate(procedure_id: str, anatomy_complexity: int, physiology: SystemsState, environment: EnvironmentState) -> ScenarioSeed:
        return ScenarioSeed(
            procedure_id=procedure_id,
            anatomy_complexity=anatomy_complexity,
            physiology_hash=physiology.deterministic_hash,
            environment_hash=environment.deterministic_hash,
        )
