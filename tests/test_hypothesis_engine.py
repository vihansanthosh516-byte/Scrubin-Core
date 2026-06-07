from scrubin.planner.hypothesis_engine import HypothesisEngine
from scrubin.planner.planner_models import PlanningRequest


def test_hypothesis_engine_returns_expected():
    request = PlanningRequest(objective="Investigate hemorrhage recovery", seed=123)
    hypos = HypothesisEngine.generate(request)
    expected = [
        "MAP decreases with blood loss.",
        "Fluids improve recovery.",
        "Older patients recover more slowly.",
    ]
    assert [h.description for h in hypos] == expected
