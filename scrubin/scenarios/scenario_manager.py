"""Deterministic scenario manager – integrates generated adversarial scenario into the simulation world.

The manager produces a new ``SimulationWorld`` (from the simulation package) with
physiological and environment modifications derived from the deterministic
scenario profile.  All updates are performed via ``replace``; no randomness is
introduced.
"""

from __future__ import annotations
from dataclasses import replace

from ..systems.models import SystemsState, CardiovascularSystem, RespiratorySystem
from ..simulation.models import SimulationWorld, EnvironmentState
from .scenario_generator import ScenarioGenerator
from .models import ScenarioSnapshot, ScenarioProfile


class ScenarioManager:
    """Orchestrate full adversarial scenario lifecycle for a simulation tick.

    ``apply`` takes the current world and returns a ``ScenarioSnapshot`` that
    contains the updated world and the deterministic ``ScenarioProfile``.
    """

    @staticmethod
    def _apply_stress(world: SimulationWorld, profile: ScenarioProfile) -> SimulationWorld:
        # Apply each stress vector deterministically.
        env = world.environment
        phys = world.physiology
        cv = phys.cardiovascular
        resp = phys.respiratory
        # Process stress vectors
        for sv in profile.stress_vectors:
            if sv.name == "hemorrhage_amplification":
                # Increase blood loss and lower MAP proportionally.
                cv = replace(cv, blood_loss=cv.blood_loss + 200.0, map=cv.map - 20.0)
            elif sv.name == "airway_obstruction":
                resp = replace(resp, oxygen_delivery=max(0.0, resp.oxygen_delivery - sv.magnitude * 0.3))
            elif sv.name == "instrument_failure":
                # Remove one instrument deterministically (first in sorted list).
                instruments = list(env.available_instruments)
                if instruments:
                    instruments.pop(0)
                env = replace(env, available_instruments=tuple(sorted(instruments)))
        # Rebuild physiology tuple with updated subsystems.
        new_phys = replace(phys, cardiovascular=cv, respiratory=resp)
        return replace(world, environment=env, physiology=new_phys)

    @staticmethod
    def _apply_failure_modes(world: SimulationWorld, profile: ScenarioProfile) -> SimulationWorld:
        # For this simple deterministic implementation, failure modes are already
        # reflected by the stress vectors; we keep the method for extensibility.
        return world

    @staticmethod
    def apply(world: SimulationWorld, procedure_id: str, anatomy_complexity: int) -> ScenarioSnapshot:
        # Generate deterministic scenario profile.
        profile: ScenarioProfile = ScenarioGenerator.generate(
            procedure_id, anatomy_complexity, world.physiology, world.environment
        )
        # Apply stress vectors and failure modes.
        new_world = ScenarioManager._apply_stress(world, profile)
        new_world = ScenarioManager._apply_failure_modes(new_world, profile)
        return ScenarioSnapshot(world=new_world, profile=profile)
