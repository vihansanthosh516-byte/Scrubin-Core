'''Tests for deterministic GoalConflictState behavior.'''

from scrubin.cognition.goal_conflict import GoalConflict, GoalConflictState


def test_conflict_add_and_ordering():
    # Two conflicts with different severities and types
    c1 = GoalConflict(
        id="c1",
        goal_a_id="g1",
        goal_b_id="g2",
        conflict_type="resource",
        severity=2.0,
        detected_tick=0,
    )
    c2 = GoalConflict(
        id="c2",
        goal_a_id="g3",
        goal_b_id="g4",
        conflict_type="physiologic",
        severity=1.0,
        detected_tick=0,
    )
    state = GoalConflictState().add_conflict(c1).add_conflict(c2)
    # Ordering: severity descending first, then type asc, then id asc
    assert state.active_conflicts[0].id == "c1"
    assert state.active_conflicts[1].id == "c2"


def test_conflict_resolution_sets_tick():
    c = GoalConflict(
        id="c3",
        goal_a_id="g5",
        goal_b_id="g6",
        conflict_type="resource",
        severity=1.0,
        detected_tick=0,
    )
    state = GoalConflictState().add_conflict(c)
    state = state.with_arbitration_tick(5)
    state = state.resolve_conflict("c3")
    assert len(state.active_conflicts) == 0
    assert any(conf.id == "c3" for conf in state.resolved_conflicts)
    resolved = next(conf for conf in state.resolved_conflicts if conf.id == "c3")
    assert resolved.resolved_tick == 5
