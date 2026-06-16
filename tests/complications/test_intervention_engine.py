"""Deterministic tests for InterventionEngine."""

import pytest

from scrubin.complications.models import Complication, ComplicationState
from scrubin.complications.intervention_engine import InterventionEngine


@pytest.fixture
def bleed_comp():
    return Complication(
        deterministic_id=10,
        complication_type="bleed",
        affected_structure="arm",
        severity=2,
        progression_stage="Active",
        activation_tick=0,
        last_update_tick=0,
        active=True,
        resolved=False,
        physiology_delta={},
        anatomy_delta={},
        metadata={},
    )

def test_basic_rules_deterministic(bleed_comp):
    state = ComplicationState(active_complications=(bleed_comp,))
    recs = InterventionEngine.evaluate(state, {}, {}, {}, {})
    actions = [r.action for r in recs.recommendations]
    # Expect actions from rule table for bleed severity 2
    assert set(actions) == {"clip_vessel", "cauterize"}
    # Order should be deterministic (by id then action)
    assert actions == sorted(actions)

def test_global_low_bp_adds_fluids():
    comp = bleed_comp()
    state = ComplicationState(active_complications=(comp,))
    phys = {"blood_pressure": 70}
    recs = InterventionEngine.evaluate(state, phys, {}, {}, {})
    actions = [r.action for r in recs.recommendations]
    # Should contain rule actions plus fluids due to low BP
    assert "administer_fluids" in actions
    # No duplicates for same action
    assert actions.count("administer_fluids") == 1

def test_replay_consistency():
    comp = bleed_comp()
    state = ComplicationState(active_complications=(comp,))
    phys = {"blood_pressure": 70}
    first = InterventionEngine.evaluate(state, phys, {}, {}, {})
    second = InterventionEngine.evaluate(state, phys, {}, {}, {})
    assert first == second
    assert first.recommendations == second.recommendations
