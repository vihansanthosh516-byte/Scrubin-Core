from scrubin.planner.constraint_engine import ConstraintEngine
from scrubin.planner.planner_models import PlanningRequest, PlannerConstraint


def test_constraint_engine_total_combos():
    request = PlanningRequest(objective="test", seed=0)
    param_grid = {
        "a": (1, 2),
        "b": (True, False),
    }
    new_grid, total = ConstraintEngine.apply(request, param_grid)
    # Ensure grid unchanged and total combos correct (2*2=4).
    assert new_grid == param_grid
    assert total == 4
