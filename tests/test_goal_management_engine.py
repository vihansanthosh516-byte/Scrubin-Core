'''Tests for GoalManagementEngine integration with IntentSynthesisEngine.'''

from scrubin.engine.random import SimulationRNG
from scrubin.cognition.intent_synthesis_engine import IntentSynthesisEngine
from scrubin.cognition.goal_management_engine import GoalManagementEngine
from scrubin.world.state import WorldState


def test_goal_creation_and_dominant_shift():
    rng = SimulationRNG(seed=0)
    intent_engine = IntentSynthesisEngine(rng)
    goal_engine = GoalManagementEngine(rng)
    # Start with an empty world
    world = WorldState(tick=0, seed=0)
    # Run intent synthesis – creates an autonomous intent and sets dominant intent
    world = intent_engine.evolve(world)
    # Run goal management – should generate a goal linked to the dominant intent
    world = goal_engine.evolve(world)

    # Verify a goal has been added
    g_state = world.goal_hierarchy_state
    assert len(g_state.active_goals) == 1
    goal = g_state.active_goals[0]
    intent = world.intentive_cognition_state.active_intents[0]
    expected_goal_id = f"goal_{intent.id}"
    assert goal.id == expected_goal_id
    # The goal description should match the intent description
    assert goal.description == intent.description
    # Verify timeline includes a goal_created event and a dominant_goal_shifted event
    descriptions = [e.description for e in world.timeline]
    assert any(desc.startswith("goal_created:") for desc in descriptions)
    assert any(desc.startswith("dominant_goal_shifted:") for desc in descriptions)
