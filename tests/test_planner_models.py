import pytest
from dataclasses import FrozenInstanceError

from scrubin.planner.planner_models import (
    PlanningRequest,
    Hypothesis,
    ParameterRange,
    PlannerConstraint,
    PlannerMetadata,
    PlanningResult,
)


def test_planner_models_are_frozen():
    request = PlanningRequest(objective="test", seed=42)
    with pytest.raises(FrozenInstanceError):
        request.objective = "new"

    hypo = Hypothesis(description="test hypothesis")
    with pytest.raises(FrozenInstanceError):
        hypo.description = "changed"

    param = ParameterRange(name="p", values=(1, 2))
    with pytest.raises(FrozenInstanceError):
        param.name = "q"

    cons = PlannerConstraint(type="max_runs")
    with pytest.raises(FrozenInstanceError):
        cons.type = "other"

    meta = PlannerMetadata(created_at="2022-01-01")
    with pytest.raises(FrozenInstanceError):
        meta.created_at = "2023-01-01"

    # PlanningResult requires a valid ExperimentDefinition – use a dummy via a simple dict placeholder is not allowed, 
    # so we just ensure the dataclass itself is immutable (cannot set attributes).
    dummy_def = None  # placeholder not used in test; we only test immutability of the container itself.
    result = PlanningResult(
        experiment_definition=dummy_def,
        hypotheses=(),
        parameter_summary={},
        estimated_run_count=0,
        planning_hash="abc",
        metadata=meta,
    )
    with pytest.raises(FrozenInstanceError):
        result.planning_hash = "def"
