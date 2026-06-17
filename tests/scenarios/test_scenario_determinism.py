"""Scenario deterministic hashing tests.

Ensures that two identical ProcedureScenario instances produce identical deterministic hashes.
"""

from __future__ import annotations

from scrubin.scenarios.models import (
    ProcedureScenario,
    PatientInfo,
    OperativeContext,
    Resources,
    Step,
)

def build_scenario() -> ProcedureScenario:
    patient = PatientInfo(
        age=30,
        sex='M',
        bmi=70.0,
        diagnosis='test',
        comorbidities=(),
        allergies=(),
        baseline_vitals={},
    )
    operative_context = OperativeContext(
        or_setup='standard',
        positioning='supine',
        anatomy_variant='normal',
        pathology_severity='moderate',
    )
    resources = Resources()
    step = Step(id='step1')
    return ProcedureScenario(
        id='test',
        display_name='Test Procedure',
        specialty='General',
        difficulty='easy',
        description='',
        patient=patient,
        operative_context=operative_context,
        resources=resources,
        workflow=(step,),
    )

def test_procedure_scenario_hash_stability():
    s1 = build_scenario()
    s2 = build_scenario()
    assert s1.deterministic_hash == s2.deterministic_hash
