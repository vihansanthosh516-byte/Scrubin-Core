"""Simulation deterministic hashing tests.

Ensures that two identical SimulationSnapshots produce identical deterministic hashes across runs.
"""

from __future__ import annotations

from scrubin.simulation.models import SimulationWorld, SimulationSnapshot, EnvironmentState
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

def build_world():
    phys = SystemsState(
        cardiovascular=CardiovascularSystem(),
        respiratory=RespiratorySystem(),
        renal=RenalSystem(),
        hepatic=HepaticSystem(),
        neurologic=NeurologicSystem(),
        endocrine=EndocrineSystem(),
        immune=ImmuneSystem(),
        metabolic=MetabolicSystem(),
    )
    env = EnvironmentState()
    return SimulationWorld(environment=env, physiology=phys, tick=0)

def test_simulation_snapshot_hash_stability():
    snap1 = SimulationSnapshot(
        world=build_world(),
        agents=tuple(),
        events=tuple(),
        actions=tuple(),
        interaction_packets=tuple(),
    )
    snap2 = SimulationSnapshot(
        world=build_world(),
        agents=tuple(),
        events=tuple(),
        actions=tuple(),
        interaction_packets=tuple(),
    )
    assert snap1.deterministic_hash == snap2.deterministic_hash
