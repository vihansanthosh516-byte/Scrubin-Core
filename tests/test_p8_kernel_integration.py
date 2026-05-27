import pytest
from scrubin.control_plane.kernel import ControlPlaneKernel


def test_kernel_p8_run_submission():
    kernel = ControlPlaneKernel(core_interface=None)
    artifact = kernel.run_simulation({"ticks": 10, "seed": 42, "initial_state": {}})
    assert artifact.run_id is not None
    assert artifact.final_state is not None


def test_kernel_p8_retrieval():
    kernel = ControlPlaneKernel(core_interface=None)
    artifact = kernel.run_simulation({"ticks": 5, "seed": 1, "initial_state": {}})
    fetched = kernel.get_run(artifact.run_id)
    assert fetched is not None
    assert fetched.run_id == artifact.run_id
