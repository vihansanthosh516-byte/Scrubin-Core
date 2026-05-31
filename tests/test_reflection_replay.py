'''Replay determinism test for ReflectionEngine integration.'''

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


def test_reflection_replay_determinism_short():
    a = _run_simulation(5)
    b = _run_simulation(5)
    assert a == b
