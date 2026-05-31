'''Tests for deterministic ReflectionState behavior.'''

from scrubin.cognition.reflection_state import ReflectionState, DecisionReflection


def test_reflection_add_and_ordering():
    r1 = DecisionReflection(id="r1", tick=1, stability_score=0.5)
    r2 = DecisionReflection(id="r2", tick=1, stability_score=0.8)
    r3 = DecisionReflection(id="r3", tick=2, stability_score=0.3)
    state = ReflectionState().add_reflection(r1).add_reflection(r2).add_reflection(r3)
    # Ordered by tick asc, stability_score desc, id asc
    # tick=1, stability desc: r2 then r1, then tick=2 r3
    assert state.reflections[0].id == "r2"
    assert state.reflections[1].id == "r1"
    assert state.reflections[2].id == "r3"


def test_reflection_compute_insight():
    # All successes => drift 0, stability 1
    r_success = DecisionReflection(id="r_success", tick=0, outcome="success")
    state = ReflectionState().add_reflection(r_success)
    state = state.compute_deterministic_insight()
    assert state.drift_index == 0.0
    assert state.stability_index == 1.0

    # One failure => drift 0.5, stability 0.5
    r_fail = DecisionReflection(id="r_fail", tick=1, outcome="failure")
    state = state.add_reflection(r_fail)
    state = state.compute_deterministic_insight()
    assert state.drift_index == 0.5
    assert state.stability_index == 0.5
