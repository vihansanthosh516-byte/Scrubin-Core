"""Deterministic tests for RecoveryPlanner and EscalationEngine."""

import pytest

from scrubin.complications.models import Complication, ComplicationState
from scrubin.complications.recovery_planner import RecoveryPlanner, RecoveryPlan
from scrubin.complications.escalation_engine import EscalationEngine


@pytest.fixture
def active_critical():
    return Complication(
        deterministic_id=1,
        complication_type="infection",
        affected_structure="lung",
        severity=3,
        progression_stage="Critical",
        activation_tick=0,
        last_update_tick=0,
        active=True,
        resolved=False,
        physiology_delta={},
        anatomy_delta={},
        metadata={},
    )

@pytest.fixture
def active_escalating():
    return Complication(
        deterministic_id=2,
        complication_type="bleed",
        affected_structure="arm",
        severity=2,
        progression_stage="Escalating",
        activation_tick=0,
        last_update_tick=0,
        active=True,
        resolved=False,
        physiology_delta={},
        anatomy_delta={},
        metadata={},
    )

def test_recovery_planner_proposes_actions(active_critical, active_escalating):
    state = ComplicationState(active_complications=(active_critical, active_escalating))
    plan, events = RecoveryPlanner.evaluate(state)
    # Should contain two actions: Critical -> Recovering, Escalating -> Critical
    assert isinstance(plan, RecoveryPlan)
    assert len(plan.actions) == 2
    ids = {a.complication_id for a in plan.actions}
    assert ids == {1, 2}
    stages = {a.new_stage for a in plan.actions}
    assert stages == {"Recovering", "Critical"}
    assert len(events) == 2

def test_escalation_engine_triggers_when_stress_high(active_critical):
    # start in Active stage to allow escalation
    comp_active = Complication(
        deterministic_id=3,
        complication_type="fracture",
        affected_structure="leg",
        severity=1,
        progression_stage="Active",
        activation_tick=0,
        last_update_tick=0,
        active=True,
        resolved=False,
        physiology_delta={},
        anatomy_delta={},
        metadata={},
    )
    state = ComplicationState(active_complications=(comp_active,))
    phys = {"stress": 10}
    anat = {"damage": 0}
    team = {"staff_available": 2}
    wf = {}
    new_state, evs = EscalationEngine.evaluate(state, phys, anat, team, wf)
    # Expect progression_stage changed to Escalating
    updated = new_state.active_complications[0]
    assert updated.progression_stage == "Escalating"
    assert len(evs) == 1
    assert evs[0].event_type == "escalated"

def test_escalation_engine_no_change_when_below_threshold(active_critical):
    state = ComplicationState(active_complications=(active_critical,))
    phys = {"stress": 1}
    anat = {"damage": 0}
    team = {"staff_available": 2}
    wf = {}
    new_state, evs = EscalationEngine.evaluate(state, phys, anat, team, wf)
    # No escalation because not in Active stage
    assert new_state == state
    assert evs == ()

def test_hash_consistency_after_escalation(active_critical):
    comp = Complication(
        deterministic_id=4,
        complication_type="infection",
        affected_structure="lung",
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
    state = ComplicationState(active_complications=(comp,))
    phys = {"stress": 6}
    new_state, _ = EscalationEngine.evaluate(state, phys, {}, {"staff_available": 1}, {})
    # hash should be deterministic and differ from original
    assert new_state.deterministic_hash != state.deterministic_hash
