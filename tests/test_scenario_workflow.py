"""Tests for deterministic scenario workflow engine."""

from scrubin.scenarios.models import ProcedureScenario, PatientInfo, OperativeContext, Resources, Step
from scrubin.scenarios.workflow_engine import ScenarioWorkflowEngine


def make_simple_scenario(id_: str, steps: list[str]):
    workflow = tuple(Step(id=s) for s in steps)
    patient = PatientInfo(age=30, sex="M", bmi=25.0, diagnosis="test", comorbidities=(), allergies=(), baseline_vitals={})
    operative_context = OperativeContext(or_setup="standard", positioning="supine", anatomy_variant="normal", pathology_severity="moderate")
    resources = Resources(instruments=("scalpel", "forceps"), staff=("surgeon",), medications=(), implants=(), equipment=())
    return ProcedureScenario(
        id=id_,
        display_name="Test Procedure",
        specialty="General",
        difficulty="easy",
        description="",
        patient=patient,
        operative_context=operative_context,
        resources=resources,
        workflow=workflow,
        complications=(),
        success_conditions=("step_completed(step2)",),
        failure_conditions=(),
        teaching_objectives=(),
        estimated_duration_minutes=30,
        educational={},
    )

def test_basic_progression():
    scenario = make_simple_scenario("test1", ["step1", "step2", "step3"])
    engine = ScenarioWorkflowEngine(scenario)
    # Initially no step executed, next available should be first step.
    assert engine.next_available_steps() == ("step1",)
    # Execute step1
    state, events = engine.execute_step("step1")
    # Update engine's internal state
    engine.state = state
    assert any(e["type"] == "StepCompleted" and e["step"] == "step1" for e in events)
    # Next available should be step2
    assert engine.next_available_steps() == ("step2",)
    # Execute step2
    state, events = engine.execute_step("step2")
    engine.state = state
    # Verify success condition met (step_completed(step2))
    success, msgs = engine.evaluate_outcome()
    assert success
    assert not msgs

def test_prerequisite_logic():
    # step2 requires step1 completed
    step1 = Step(id="step1")
    step2 = Step(id="step2", prerequisite_steps=("step1",))
    scenario = ProcedureScenario(
        id="test2",
        display_name="Prereq",
        specialty="General",
        difficulty="easy",
        description="",
        patient=PatientInfo(age=30, sex="M", bmi=25.0, diagnosis="", comorbidities=(), allergies=(), baseline_vitals={}),
        operative_context=OperativeContext(or_setup="standard", positioning="supine", anatomy_variant="normal", pathology_severity="moderate"),
        resources=Resources(instruments=("scalpel",), staff=("surgeon",), medications=(), implants=(), equipment=()),
        workflow=(step1, step2),
        complications=(),
        success_conditions=("step_completed(step2)",),
        failure_conditions=(),
        teaching_objectives=(),
        estimated_duration_minutes=30,
        educational={},
    )
    engine = ScenarioWorkflowEngine(scenario)
    # Initially only step1 is available
    assert engine.next_available_steps() == ("step1",)
    # Try to execute step2 directly – should be blocked
    state, events = engine.execute_step("step2")
    assert any(e["type"] == "StepBlocked" for e in events)
    # Execute step1 then step2
    state, _ = engine.execute_step("step1")
    engine.state = state
    assert engine.next_available_steps() == ("step2",)
    state, _ = engine.execute_step("step2")
    engine.state = state
    success, _ = engine.evaluate_outcome()
    assert success

def test_resource_requirement_failure():
    # step1 requires an instrument not present in scenario resources
    step1 = Step(id="step1", required_instruments=("nonexistent",))
    scenario = ProcedureScenario(
        id="test3",
        display_name="ResourceFail",
        specialty="General",
        difficulty="easy",
        description="",
        patient=PatientInfo(age=30, sex="M", bmi=25.0, diagnosis="", comorbidities=(), allergies=(), baseline_vitals={}),
        operative_context=OperativeContext(or_setup="standard", positioning="supine", anatomy_variant="normal", pathology_severity="moderate"),
        resources=Resources(instruments=("scalpel",), staff=("surgeon",), medications=(), implants=(), equipment=()),
        workflow=(step1,),
        complications=(),
        success_conditions=(),
        failure_conditions=(),
        teaching_objectives=(),
        estimated_duration_minutes=30,
        educational={},
    )
    engine = ScenarioWorkflowEngine(scenario)
    # Attempt to execute step1 – should fail due to missing resource.
    state, events = engine.execute_step("step1")
    assert any(e["type"] == "StepFailed" and e["reason"] == "resources_unavailable" for e in events)
    # Step should be recorded in failed_steps.
    assert "step1" in state.failed_steps
