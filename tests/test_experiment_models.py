import pytest
from dataclasses import FrozenInstanceError

from scrubin.experiments.experiment_models import (
    ExperimentDefinition,
    ExperimentRun,
    ExperimentStatus,
    ExperimentSummary,
    ParameterSweep,
    ExperimentArtifact,
)


def test_experiment_models_are_frozen():
    definition = ExperimentDefinition(name="exp1")
    with pytest.raises(FrozenInstanceError):
        definition.name = "new"

    run = ExperimentRun(run_id="r1", experiment_name="exp1")
    with pytest.raises(FrozenInstanceError):
        run.run_id = "r2"

    status = ExperimentStatus(total=1, queued=1, running=0, completed=0, failed=0)
    with pytest.raises(FrozenInstanceError):
        status.total = 2

    summary = ExperimentSummary(
        experiment_name="exp1",
        total_runs=1,
        completed_runs=0,
        failed_runs=0,
        mean_ticks=0.0,
        min_ticks=0,
        max_ticks=0,
    )
    with pytest.raises(FrozenInstanceError):
        summary.total_runs = 2

    sweep = ParameterSweep(combos=((('a', 1),), (('a', 2),)))
    with pytest.raises(FrozenInstanceError):
        sweep.combos = ()

    artifact = ExperimentArtifact(run_id="r1", artifact=None)
    with pytest.raises(FrozenInstanceError):
        artifact.run_id = "r2"
