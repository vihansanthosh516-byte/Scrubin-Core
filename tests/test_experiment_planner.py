from scrubin.planner.experiment_planner import ExperimentPlanner
from scrubin.planner.planner_models import PlanningRequest, PlannerConstraint


def test_experiment_planner_basic():
    # Simple request without constraints.
    request = PlanningRequest(objective="Test objective", seed=7)
    planner = ExperimentPlanner(kernel=None)  # Kernel not used for planning.
    result = planner.plan(request)
    # Verify experiment definition name is deterministic based on hash.
    expected_hash_prefix = "plan_" + __import__('hashlib').sha256(f"{request.objective}{request.seed}".encode()).hexdigest()[:8]
    assert result.experiment_definition.name.startswith("plan_")
    assert result.experiment_definition.name == expected_hash_prefix
    # Expected parameters from default grid.
    expected_params = {
        "blood_loss": (0.1, 0.2, 0.3),
        "fluids": (False, True),
        "age": (20, 50, 80),
    }
    assert result.experiment_definition.parameters == expected_params
    # Estimated run count = seeds * combos = 1 * (3*2*3) = 18.
    assert result.estimated_run_count == 18
    # Hypotheses should match the base list.
    expected_hypos = [
        "MAP decreases with blood loss.",
        "Fluids improve recovery.",
        "Older patients recover more slowly.",
    ]
    assert [h.description for h in result.hypotheses] == expected_hypos
    # Planning hash should be deterministic – recompute and compare.
    import json, hashlib
    hash_input = json.dumps({
        "objective": request.objective,
        "seed": request.seed,
        "parameters": {k: list(v) for k, v in expected_params.items()},
        "constraints": [],
        "max_runs": 0,
        "metadata": {},
    }, sort_keys=True).encode()
    expected_hash = hashlib.sha256(hash_input).hexdigest()
    assert result.planning_hash == expected_hash


def test_experiment_planner_respects_max_runs():
    # Request with max_runs constraint; should cap estimated run count.
    request = PlanningRequest(objective="Obj", seed=1, max_runs=5)
    planner = ExperimentPlanner(kernel=None)
    result = planner.plan(request)
    assert result.estimated_run_count == 5
