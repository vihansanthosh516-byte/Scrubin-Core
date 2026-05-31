'''Tests for CognitiveArbitrationEngine – conflict detection and resolution.'''

from scrubin.engine.random import SimulationRNG
from scrubin.cognition.arbitration_engine import CognitiveArbitrationEngine
from scrubin.cognition.goal_state import GoalNode, GoalHierarchyState
from scrubin.cognition.intentive_state import AutonomousIntent, IntentiveCognitionState
from scrubin.world.state import WorldState


def _build_world_with_conflict():
    # Two goals that share a required concept causing a conflict
    g1 = GoalNode(
        id="g1",
        required_concepts=("c_shared",),
        priority=5.0,
        urgency=0.5,
        confidence=0.9,
    )
    g2 = GoalNode(
        id="g2",
        required_concepts=("c_shared",),
        priority=1.0,
        urgency=0.2,
        confidence=0.8,
    )
    goal_state = GoalHierarchyState().add_goal(g1).add_goal(g2).compute_dominant_goal()
    # Two intents each associated with one of the goals
    i1 = AutonomousIntent(
        id="i1",
        description="intent 1",
        urgency=0.5,
        confidence=0.9,
        originating_goal="g1",
    )
    i2 = AutonomousIntent(
        id="i2",
        description="intent 2",
        urgency=0.2,
        confidence=0.8,
        originating_goal="g2",
    )
    intent_state = (
        IntentiveCognitionState()
        .add_intent(i1)
        .add_intent(i2)
        .compute_dominant_intent()
    )
    world = WorldState(tick=0, seed=0, goal_hierarchy_state=goal_state, intentive_cognition_state=intent_state)
    return world


def test_arbitration_detects_and_resolves_conflict():
    rng = SimulationRNG(seed=0)
    engine = CognitiveArbitrationEngine(rng)
    world = _build_world_with_conflict()
    # Before arbitration, both goals are active
    assert len(world.goal_hierarchy_state.active_goals) == 2
    # Evolve arbitration engine
    world = engine.evolve(world)
    # After arbitration, the lower‑scoring goal (g2) should be abandoned
    active_ids = {g.id for g in world.goal_hierarchy_state.active_goals}
    assert "g2" not in active_ids
    # All intents tied to the abandoned goal should be removed
    intent_origins = {i.originating_goal for i in world.intentive_cognition_state.active_intents}
    assert "g2" not in intent_origins
    # Verify deterministic events were emitted
    descriptions = [e.description for e in world.timeline]
    assert any(d.startswith("goal_conflict_detected:") for d in descriptions)
    assert any(d.startswith("goal_arbitrated:") for d in descriptions)
    assert any(d.startswith("goal_suppressed:") for d in descriptions)
    assert any(d.startswith("conflict_resolved:") for d in descriptions)
