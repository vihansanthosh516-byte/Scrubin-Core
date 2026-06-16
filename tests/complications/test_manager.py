"""Deterministic tests for the complications manager.
"""

import pytest

from scrubin.complications.manager import ComplicationManager
from scrubin.complications.models import Complication, ComplicationState


@pytest.fixture
def base_complication():
    return Complication(
        deterministic_id=1,
        complication_type="infection",
        affected_structure="lung",
        severity=1,
        progression_stage="Inactive",
        activation_tick=0,
        last_update_tick=0,
        active=False,
        resolved=False,
        physiology_delta={},
        anatomy_delta={},
        metadata={},
    )


def test_activation_and_hash_stability(base_complication):
    state = ComplicationState()
    state1, ev = ComplicationManager.activate(state, base_complication, tick=10)
    assert ev.event_type == "activated"
    assert ev.tick == 10
    assert state1.deterministic_hash == hash(((1,), ()))

    # activating the same complication again should not change hash
    state2, _ = ComplicationManager.activate(state1, base_complication, tick=20)
    assert state2.deterministic_hash == state1.deterministic_hash


def test_progression_and_resolution(base_complication):
    state = ComplicationState()
    state, _ = ComplicationManager.activate(state, base_complication, tick=5)
    # progress to Escalating
    state, ev = ComplicationManager.update(state, comp_id=1, tick=6, new_stage="Escalating", severity=2)
    assert ev.details["stage"] == "Escalating"
    assert ev.details["severity"] == 2
    # resolve
    state, ev = ComplicationManager.resolve(state, comp_id=1, tick=8)
    assert ev.event_type == "resolved"
    # after resolution, hash reflects empty active and one resolved
    assert state.deterministic_hash == hash((( ), (1,)))
    assert len(state.active_complications) == 0
    assert len(state.resolved_complications) == 1


def test_deterministic_ordering():
    comp_a = Complication(
        deterministic_id=2,
        complication_type="bleed",
        affected_structure="arm",
        severity=1,
        progression_stage="Inactive",
        activation_tick=0,
        last_update_tick=0,
        active=False,
        resolved=False,
        physiology_delta={},
        anatomy_delta={},
        metadata={},
    )
    comp_b = Complication(
        deterministic_id=1,
        complication_type="fracture",
        affected_structure="leg",
        severity=1,
        progression_stage="Inactive",
        activation_tick=0,
        last_update_tick=0,
        active=False,
        resolved=False,
        physiology_delta={},
        anatomy_delta={},
        metadata={},
    )
    state = ComplicationState()
    state, _ = ComplicationManager.activate(state, comp_a, tick=1)
    state, _ = ComplicationManager.activate(state, comp_b, tick=2)
    hash1 = state.deterministic_hash

    state2 = ComplicationState()
    state2, _ = ComplicationManager.activate(state2, comp_b, tick=1)
    state2, _ = ComplicationManager.activate(state2, comp_a, tick=2)
    assert state2.deterministic_hash == hash1
