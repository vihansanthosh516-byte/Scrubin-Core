from scrubin.experiments.experiment_manager import ExperimentManager
from scrubin.control_plane.kernel import ControlPlaneKernel
from scrubin.experiments.experiment_models import ExperimentDefinition


def test_parameter_sweep_deterministic_order():
    kernel = ControlPlaneKernel(core_interface=None)
    manager = ExperimentManager(kernel)
    definition = ExperimentDefinition(
        name="test_exp",
        seeds=(1,),
        tick_count=1,
        parameters={
            "alpha": (1, 2),
            "beta": ("x", "y"),
        },
    )
    sweep = manager._generate_parameter_sweep(definition)
    # Expected order: alpha first, then beta
    expected = [
        (('alpha', 1), ('beta', 'x')),
        (('alpha', 1), ('beta', 'y')),
        (('alpha', 2), ('beta', 'x')),
        (('alpha', 2), ('beta', 'y')),
    ]
    assert sweep.combos == tuple(expected)
