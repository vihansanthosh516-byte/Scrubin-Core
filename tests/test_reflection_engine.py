'''Tests for ReflectionEngine – ensures reflections are generated each tick.'''

from scrubin.engine.random import SimulationRNG
from scrubin.cognition.reflection_engine import ReflectionEngine
from scrubin.world.state import WorldState


def test_reflection_engine_generates_reflection_and_events():
    rng = SimulationRNG(seed=0)
    engine = ReflectionEngine(rng)
    world = WorldState(tick=0, seed=0)
    # Evolve one tick with engine
    world = engine.evolve(world)
    # Verify a reflection was added
    assert hasattr(world, "reflection_state")
    assert len(world.reflection_state.reflections) == 1
    # Verify timeline includes reflection_created event
    descriptions = [e.description for e in world.timeline]
    assert any(d.startswith("reflection_created:") for d in descriptions)
