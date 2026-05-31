import pytest

from scrubin.engine.random import SimulationRNG
from scrubin.world.state import WorldState
from scrubin.cognition.learning_state import LearningState, LearningObservation
from scrubin.cognition.intent_synthesis_engine import IntentSynthesisEngine
from scrubin.cognition.goal_management_engine import GoalManagementEngine
from scrubin.cognition.arbitration_engine import CognitiveArbitrationEngine
from scrubin.ontology.executive_planner import ExecutivePlanner
from scrubin.ontology.intent_scheduler import IntentScheduler
from scrubin.runtime.state_hashing import deterministic_world_hash

# Helper to run the isolated pipeline of cognition engines.
def run_pipeline(world: WorldState, rng: SimulationRNG) -> WorldState:
    # Intent synthesis
    world = IntentSynthesisEngine(rng).evolve(world)
    # Goal management
    world = GoalManagementEngine(rng).evolve(world)
    # Arbitration
    world = CognitiveArbitrationEngine(rng).evolve(world)
    # Planning (ExecutivePlanner) – deterministic plan step
    world = ExecutivePlanner(rng).plan(world)
    # Intent scheduling
    world = IntentScheduler(rng).schedule(world)
    return world


def test_learning_state_does_not_influence_cognition_outputs():
    rng = SimulationRNG(0)
    base_world = WorldState(tick=0, seed=0)

    # World with an empty LearningState (default)
    world_empty = base_world.with_learning_state(LearningState())
    # World with a non‑empty LearningState (one dummy observation). This should not affect the engines under test.
    dummy_observation = LearningObservation(
        id="obs_dummy",
        tick=0,
        source_reflection_id="ref_dummy",
        category="dummy",
        lesson="dummy lesson",
        confidence=1.0,
        severity=0.0,
        tags=(),
    )
    filled_state = LearningState(
        observations=(dummy_observation,),
        patterns=(),
        beliefs=(),
        total_observations=1,
    )
    world_filled = base_world.with_learning_state(filled_state)

    # Run identical pipelines on both worlds.
    result_empty = run_pipeline(world_empty, rng)
    result_filled = run_pipeline(world_filled, rng)

    # Strip learning_state so that any internal differences do not affect comparison.
    result_empty = result_empty.with_learning_state(LearningState())
    result_filled = result_filled.with_learning_state(LearningState())

    # Deterministic hash of the resulting worlds should be identical.
    assert deterministic_world_hash(result_empty) == deterministic_world_hash(result_filled)

    # As an additional safeguard, the dataclasses should be equal after stripping learning state.
    assert result_empty == result_filled
