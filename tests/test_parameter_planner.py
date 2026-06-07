from scrubin.planner.parameter_planner import ParameterPlanner
from scrubin.planner.planner_models import PlanningRequest


def test_parameter_planner_default_grid():
    request = PlanningRequest(objective="test", seed=0)
    grid = ParameterPlanner.generate(request)
    expected = {
        "blood_loss": (0.1, 0.2, 0.3),
        "fluids": (False, True),
        "age": (20, 50, 80),
    }
    assert grid == expected
