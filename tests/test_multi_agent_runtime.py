"""Deterministic multi‑agent runtime tests.

These tests verify that the deterministic actor updates, event emission, and
replay safety work as expected.
"""

from __future__ import annotations

from scrubin.world.state import WorldState
from scrubin.agents.state import default_actors, OperativeActor
from scrubin.agents.runtime_engine import MultiAgentRuntimeEngine
from scrubin.engine.random import SimulationRNG


def _make_engine_and_world():
    rng = SimulationRNG(seed=0)
    engine = MultiAgentRuntimeEngine(rng)
    world = WorldState(tick=0, seed=0)
    world = world.with_actors(default_actors())
    return engine, world


def test_fatigue_accumulates():
    engine, world = _make_engine_and_world()
    # Run a few ticks – fatigue should increase for each actor
    for _ in range(5):
        world = engine.evolve(world)
    # Verify that at least one actor has non‑zero fatigue
    assert any(actor.fatigue > 0.0 for actor in world.actors)


def test_communication_breakdown_event():
    engine, world = _make_engine_and_world()
    # Add many tasks to the primary surgeon to push cognitive load above threshold
    surgeon = next(a for a in world.actors if a.role == "primary_surgeon")
    heavy_queue = tuple(f"task{i}" for i in range(50))
    surgeon = surgeon.with_task_queue(heavy_queue)
    world = world.with_actor(surgeon)
    # Evolve until an event is emitted
    for _ in range(3):
        world = engine.evolve(world)
    # Event should be present in timeline
    assert any("communication_breakdown:primary_surgeon" in ev.description for ev in world.timeline)


def test_replay_consistency():
    def run():
        engine, world = _make_engine_and_world()
        for _ in range(4):
            world = engine.evolve(world)
        return world
    w1 = run()
    w2 = run()
    assert w1 == w2
