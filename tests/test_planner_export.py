from scrubin.planner.planner_export import export_planning_request_to_json, export_planning_result_to_json, export_parameter_grid_to_csv
from scrubin.planner.planner_models import PlanningRequest, PlanningResult, Hypothesis, PlannerMetadata
from scrubin.planner.experiment_planner import ExperimentPlanner


def test_export_planning_request_json():
    request = PlanningRequest(objective="Obj", seed=3, max_runs=0)
    json_str = export_planning_request_to_json(request)
    # Deterministic field order – should contain objective, seed, constraints, max_runs, metadata.
    assert '"objective":"Obj"' in json_str
    assert '"seed":3' in json_str
    assert '"max_runs":0' in json_str


def test_export_planning_result_json():
    request = PlanningRequest(objective="Obj", seed=3)
    planner = ExperimentPlanner(kernel=None)
    result = planner.plan(request)
    json_str = export_planning_result_to_json(result)
    # Verify crucial fields are present.
    assert result.planning_hash in json_str
    assert result.experiment_definition.name in json_str
    assert '"hypotheses"' in json_str


def test_export_parameter_grid_csv():
    request = PlanningRequest(objective="Obj", seed=1)
    csv_str = export_parameter_grid_to_csv(request)
    # Header should contain the three default parameter names in alphabetical order.
    header = csv_str.splitlines()[0]
    assert header == 'age,blood_loss,fluids'
    # Number of rows should equal 3*3*2 = 18 combos plus header.
    rows = csv_str.strip().splitlines()
    assert len(rows) == 19
