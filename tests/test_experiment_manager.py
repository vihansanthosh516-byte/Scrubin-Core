from scrubin.control_plane.kernel import ControlPlaneKernel
from scrubin.experiments.experiment_manager import ExperimentManager
from scrubin.experiments.experiment_models import ExperimentDefinition


def test_experiment_creation_and_run_order():
    kernel = ControlPlaneKernel(core_interface=None)
    manager = ExperimentManager(kernel)
    definition = ExperimentDefinition(
        name="order_test",
        seeds=(2, 1),
        tick_count=1,
        parameters={
            "p": (10, 5),
        },
    )
    manager.create_experiment(definition)
    runs = manager.get_runs("order_test")
    # Expect product size = 2 values * 2 seeds = 4 runs
    assert len(runs) == 4
    # Verify deterministic ordering: params then seed
    # Since param tuple is (('p', value)), sorting on params then seed yields
    # first with smaller param value (5) then larger (10), and within same param, lower seed first.
    expected_order = [
        (5, 1),
        (5, 2),
        (10, 1),
        (10, 2),
    ]
    actual_order = [(run.params[0][1], run.seed) for run in runs]
    assert actual_order == expected_order

def test_experiment_execution_and_summary():
    kernel = ControlPlaneKernel(core_interface=None)
    manager = ExperimentManager(kernel)
    definition = ExperimentDefinition(
        name="run_exec",
        seeds=(1, 2),
        tick_count=3,
        parameters={},
    )
    manager.create_experiment(definition)
    manager.schedule_and_execute("run_exec")
    summary = manager.summarize("run_exec")
    # All runs should be completed and have the same tick count (metadata ticks)
    assert summary["total_runs"] == 2
    assert summary["completed_runs"] == 2
    assert summary["failed_runs"] == 0
    # Mean ticks should equal the defined tick count (metadata stores 'ticks')
    assert summary["mean_ticks"] == 3
    assert summary["min_ticks"] == 3
    assert summary["max_ticks"] == 3
