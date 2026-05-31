import pytest

from scrubin.engine.random import SimulationRNG
from scrubin.engine.physiologic_evolution import PhysiologicEvolutionEngine
from scrubin.world.state import WorldState
from scrubin.runtime.state_hashing import deterministic_world_hash


def run_simulation(seed: int, ticks: int) -> WorldState:
    rng = SimulationRNG(seed)
    engine = PhysiologicEvolutionEngine(rng)
    world = WorldState(tick=0, seed=seed)
    for _ in range(ticks):
        world = engine.evolve(world)
    return world


def test_learning_replay_is_deterministic():
    seed = 42
    ticks = 5
    world_a = run_simulation(seed, ticks)
    world_b = run_simulation(seed, ticks)
    # The entire world state, including LearningState, should be identical.
    assert deterministic_world_hash(world_a) == deterministic_world_hash(world_b)
    # Direct dataclass equality should also hold.
    assert world_a == world_b
