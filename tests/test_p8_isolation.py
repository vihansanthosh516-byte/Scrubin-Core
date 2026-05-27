from scrubin.control_plane.p8.isolation_engine import IsolationEngine
from scrubin.control_plane.p8.run_manager import RunManager
from scrubin.control_plane.p8.dummy_kernel import DummyKernel


def test_isolation_independence():
    engine = IsolationEngine(kernel_cls=DummyKernel)
    mgr = RunManager(engine)

    r1 = mgr.submit({"ticks": 10, "seed": 1})
    r2 = mgr.submit({"ticks": 10, "seed": 2})

    assert r1.run_id != r2.run_id
    assert r1.final_state != r2.final_state


def test_determinism_same_seed():
    engine = IsolationEngine(kernel_cls=DummyKernel)
    mgr = RunManager(engine)

    r1 = mgr.submit({"ticks": 10, "seed": 42})
    r2 = mgr.submit({"ticks": 10, "seed": 42})

    assert r1.metadata["hash"] == r2.metadata["hash"]
