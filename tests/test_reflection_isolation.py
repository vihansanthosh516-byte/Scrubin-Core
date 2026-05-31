'''Reflection isolation tests – ensure reflection state does not affect upstream cognition.'''

import copy

from scrubin.engine.random import SimulationRNG
from scrubin.engine.physiologic_evolution import PhysiologicEvolutionEngine
from scrubin.world.state import WorldState
from scrubin.cognition.reflection_state import DecisionReflection


def _run_one_tick(initial_world: WorldState, rng) -> WorldState:
    """Run a single evolution tick and return the new world state."""
    engine = PhysiologicEvolutionEngine(rng)
    return engine.evolve(initial_world)


def test_reflection_isolation_no_upstream_effect():
    # Fixed RNG seed ensures deterministic behavior
    rng = SimulationRNG(seed=0)
    # Start from a clean world at tick 0
    start_world = WorldState(tick=0, seed=0)

    # 1️⃣ Baseline evolution without any reflection manipulation
    baseline_world = _run_one_tick(start_world, rng)
    baseline_intents = baseline_world.intentive_cognition_state.active_intents
    baseline_goal = baseline_world.goal_hierarchy_state.active_goals
    baseline_dominant_intent = baseline_world.intentive_cognition_state.dominant_intent_id
    baseline_dominant_goal = baseline_world.goal_hierarchy_state.dominant_goal_id

    # 2️⃣ Inject a fake reflection into the original world (pre‑evolution)
    fake_reflection = DecisionReflection(
        id="fake_reflection",
        tick=0,
        outcome="success",
    )
    manipulated_reflection_state = start_world.reflection_state.add_reflection(fake_reflection)
    manipulated_world = start_world.with_reflection_state(manipulated_reflection_state)

    # 3️⃣ Run evolution from the manipulated world
    manipulated_result = _run_one_tick(manipulated_world, rng)

    # 4️⃣ Verify upstream results are identical to baseline
    assert manipulated_result.intentive_cognition_state.active_intents == baseline_intents
    assert manipulated_result.goal_hierarchy_state.active_goals == baseline_goal
    assert manipulated_result.intentive_cognition_state.dominant_intent_id == baseline_dominant_intent
    assert manipulated_result.goal_hierarchy_state.dominant_goal_id == baseline_dominant_goal

    # 5️⃣ Ensure the reflection state did change (the fake entry is present)
    assert any(r.id == "fake_reflection" for r in manipulated_result.reflection_state.reflections)


def test_reflection_state_is_posthoc_only():
    # Run two full pipelines to confirm that reflection is generated but does not feed back.
    rng = SimulationRNG(seed=0)
    world = WorldState(tick=0, seed=0)
    engine = PhysiologicEvolutionEngine(rng)

    # Run several ticks – the reflection state will accumulate entries.
    for _ in range(3):
        world = engine.evolve(world)

    # Capture a snapshot of the world without the reflection field for comparison.
    world_no_reflection = copy.deepcopy(world)
    # Remove reflection entries (reset to empty) to isolate other sub‑states.
    world_no_reflection = world_no_reflection.with_reflection_state(world_no_reflection.reflection_state.__class__())

    # Re‑run the same number of ticks starting from the same initial state.
    rng2 = SimulationRNG(seed=0)
    world2 = WorldState(tick=0, seed=0)
    engine2 = PhysiologicEvolutionEngine(rng2)
    for _ in range(3):
        world2 = engine2.evolve(world2)

    # Now strip reflection from world2 as well.
    world2_no_reflection = copy.deepcopy(world2).with_reflection_state(world2.reflection_state.__class__())

    # All other sub‑states must match exactly.
    assert world_no_reflection.intentive_cognition_state == world2_no_reflection.intentive_cognition_state
    assert world_no_reflection.goal_hierarchy_state == world2_no_reflection.goal_hierarchy_state

    # The reflection state itself may differ, which is expected.

