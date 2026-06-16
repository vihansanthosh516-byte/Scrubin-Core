'''Tests for deterministic OR team engine integration.'''

from scrubin.scenarios.models import ProcedureScenario, PatientInfo, OperativeContext, Resources, Step, TeamRole
from scrubin.scenarios.workflow_engine import ScenarioWorkflowEngine


def make_team_scenario():
    team_roles = (
        TeamRole(id='surgeon1', role_type='PrimarySurgeon'),
        TeamRole(id='nurse1', role_type='ScrubNurse'),
    )
    step = Step(id='incision', required_instruments=('scalpel',), required_roles=('PrimarySurgeon',))
    patient = PatientInfo(age=30, sex='M', bmi=25.0, diagnosis='test', comorbidities=(), allergies=(), baseline_vitals={})
    operative_context = OperativeContext(or_setup='standard', positioning='supine', anatomy_variant='normal', pathology_severity='moderate')
    resources = Resources(instruments=('scalpel',), staff=('surgeon',), medications=(), implants=(), equipment=())
    return ProcedureScenario(
        id='team_test',
        display_name='Team Test',
        specialty='General',
        difficulty='easy',
        description='',
        patient=patient,
        operative_context=operative_context,
        resources=resources,
        workflow=(step,),
        complications=(),
        success_conditions=(),
        failure_conditions=(),
        teaching_objectives=(),
        estimated_duration_minutes=30,
        educational={},
        team_roles=team_roles,
    )


def test_team_task_success():
    scenario = make_team_scenario()
    engine = ScenarioWorkflowEngine(scenario)
    assert engine.next_available_steps() == ('incision',)
    state, events = engine.execute_step('incision')
    engine.state = state
    assert any(e['type'] == 'StepCompleted' and e['step'] == 'incision' for e in events)
    expected_sequence = ['InstrumentRequested', 'InstrumentAcknowledged', 'InstrumentInUse', 'TaskAssigned', 'TaskCompleted']
    actual_sequence = [e['type'] for e in events if e['type'] != 'StepCompleted']
    assert actual_sequence == expected_sequence
    team_state = engine.team_state
    surgeon = next(m for m in team_state.members if m.role_type == 'PrimarySurgeon')
    assert surgeon.workload == 1
    instrument = next(i for i in team_state.instruments if i.id == 'scalpel')
    assert instrument.status == 'available'