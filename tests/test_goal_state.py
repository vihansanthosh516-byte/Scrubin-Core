'''Tests for GoalHierarchyState and GoalNode deterministic behavior.'''

from scrubin.cognition.goal_state import GoalNode, GoalHierarchyState


def test_goal_node_helpers_and_sorting():
    # Create a goal with unsorted tuple fields
    goal = GoalNode(
        id="g1",
        required_concepts=("z", "a", "m"),
        blocking_conditions=("c", "b"),
    )
    # Verify tuple fields are sorted by the with_* helpers
    sorted_goal = goal.with_required_concepts(("z", "a", "m"))
    assert sorted_goal.required_concepts == ("a", "m", "z")
    sorted_goal = goal.with_blocking_conditions(("c", "b"))
    assert sorted_goal.blocking_conditions == ("b", "c")


def test_goal_hierarchy_add_and_dominant_selection():
    g_low = GoalNode(id="a", urgency=0.2, priority=1.0, confidence=0.9)
    g_high = GoalNode(id="b", urgency=0.5, priority=0.5, confidence=0.5)
    # Add in reverse order to test sorting by id
    state = GoalHierarchyState().add_goal(g_high).add_goal(g_low)
    # Active goals should be sorted by id (a, b)
    assert state.active_goals == (g_low, g_high)
    # Dominant goal should be the one with higher urgency (g_high)
    state = state.compute_dominant_goal()
    assert state.dominant_goal.id == "b"

    # Adding a higher priority goal should affect dominance when urgencies equal
    g_equal_urgency = GoalNode(id="c", urgency=0.5, priority=2.0, confidence=0.4)
    state = state.add_goal(g_equal_urgency)
    state = state.compute_dominant_goal()
    # Now g_equal_urgency has same urgency as dominant but higher priority
    assert state.dominant_goal.id == "c"
