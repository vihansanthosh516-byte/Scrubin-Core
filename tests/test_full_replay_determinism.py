"""Deterministic replay validation for the adaptive runtime.

The test runs the full physiologic evolution pipeline (including the O.6
adaptive stages) for a range of tick counts and verifies that two independent
runs with the same seed produce identical ``WorldState`` instances.
"""

from scrubin.world.state import WorldState
from scrubin.engine.physiologic_evolution import PhysiologicEvolutionEngine
from scrubin.engine.random import SimulationRNG


def _run_simulation(ticks: int, seed: int = 0) -> WorldState:
    rng = SimulationRNG(seed=seed)
    engine = PhysiologicEvolutionEngine(rng)
    world = WorldState(tick=0, seed=seed)
    for _ in range(ticks):
        world = engine.evolve(world)
    return world


def test_replay_determinism_10_ticks():
    a = _run_simulation(10)
    b = _run_simulation(10)
    assert a == b


def test_replay_determinism_100_ticks():
    a = _run_simulation(100)
    b = _run_simulation(100)
    assert a == b

def test_replay_determinism_1000_ticks():
    a = _run_simulation(1000)
    b = _run_simulation(1000)
    assert a == b
