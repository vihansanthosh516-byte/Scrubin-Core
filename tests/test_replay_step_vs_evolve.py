"""Test that an engine's `evolve` and `step` interfaces (if both exist) produce identical deterministic results.

The repository currently does not have an engine exposing both methods, so the test will be skipped.
"""

import copy
import pytest

# Import the deterministic world hashing utility.
from scrubin.runtime.state_hashing import deterministic_world_hash

# Attempt to import a representative engine. We use PhysiologicEvolutionEngine as a
# typical deterministic engine. If the engine does not expose a `step` method the
# test will be skipped.
from scrubin.engine.physiologic_evolution import PhysiologicEvolutionEngine
from scrubin.engine.random import SimulationRNG
from scrubin.world.state import WorldState


def _has_step_and_evolve(engine: object) -> bool:
    """Return True if the engine implements both ``evolve`` and ``step`` methods.
    """
    return hasattr(engine, "evolve") and hasattr(engine, "step")


def test_evolve_vs_step_consistency():
    rng = SimulationRNG(seed=123)
    engine = PhysiologicEvolutionEngine(rng)

    # Skip the test if the engine does not provide both interfaces.
    if not _has_step_and_evolve(engine):
        pytest.skip("Engine does not implement both evolve and step interfaces")

    N_TICKS = 5
    # Construct an immutable initial world state.
    initial_world = WorldState(tick=0, seed=123)
    # Capture a deep copy to verify immutability after the runs.
    initial_copy = copy.deepcopy(initial_world)

    # Replay using the evolve interface.
    world_evolve = initial_world
    for _ in range(N_TICKS):
        world_evolve = engine.evolve(world_evolve)

    # Replay using the step interface.
    # NOTE: The engine is expected to be deterministic and pure, so re‑using the
    # same initial state is safe.
    world_step = initial_world
    for _ in range(N_TICKS):
        world_step = engine.step(world_step)  # type: ignore[attr-defined]

    # --- Assertions -------------------------------------------------------
    # Final world states should be exactly equal (dataclass equality is field‑wise).
    assert world_evolve == world_step, "Final WorldState differs between evolve and step"

    # Timeline events must match exactly.
    assert list(world_evolve.timeline) == list(world_step.timeline), "Timeline events differ"

    # Deterministic hashes of the final states must match.
    assert deterministic_world_hash(world_evolve) == deterministic_world_hash(world_step), "World hash mismatch"

    # The original initial state must remain unchanged.
    assert initial_world == initial_copy, "Initial WorldState was mutated during replay"
