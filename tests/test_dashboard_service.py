import json
import pytest
from fastapi.testclient import TestClient

from scrubin.server.app import app
from scrubin.server.dependency_provider import get_kernel
from scrubin.control_plane.p9_debug import DebugFacade
from scrubin.runtime.state_hashing import deterministic_world_hash

client = TestClient(app)
kernel = get_kernel()
facade = DebugFacade(kernel)

def _create_run(ticks: int = 5, seed: int = 42):
    # Directly use the kernel to create a run.
    artifact = kernel.run_simulation({"ticks": ticks, "seed": seed})
    return artifact.run_id, artifact

def test_run_summary_endpoint():
    run_id, artifact = _create_run()
    response = client.get(f"/dashboard/run/{run_id}")
    assert response.status_code == 200
    data = response.json()
    meta = getattr(artifact, "metadata", {})
    assert data["run_id"] == run_id
    assert data["seed"] == meta.get("seed")
    assert data["ticks"] == meta.get("ticks")
    assert data["hash"] == meta.get("hash")

def test_replay_endpoint_consistency():
    run_id, artifact = _create_run(ticks=3, seed=7)
    # Get replay frames via API
    resp = client.get(f"/dashboard/replay/{run_id}")
    assert resp.status_code == 200
    frames = resp.json()
    # Verify count
    expected_ticks = getattr(artifact, "metadata", {}).get("ticks")
    assert len(frames) == expected_ticks
    # Verify hashes match deterministic hash of trajectory states
    trajectory = getattr(artifact, "trajectory", [])
    for i, frame in enumerate(frames):
        state = trajectory[i]
        # Use same hashing logic as ReplayInspector (supports dict or dataclass)
    try:
        expected_hash = deterministic_world_hash(state)  # type: ignore[arg-type]
    except Exception:
        import json, hashlib
        data = json.dumps(state, sort_keys=True, separators=(",", ":"))
        expected_hash = hashlib.sha256(data.encode()).hexdigest()
        assert frame["state_hash"] == expected_hash
        # Verify tick field
        assert frame["tick"] == i

def test_compare_endpoint():
    # Same seed runs should have no divergence
    run_a, _ = _create_run(ticks=2, seed=1)
    run_b, _ = _create_run(ticks=2, seed=1)
    resp = client.get(f"/dashboard/compare/{run_a}/{run_b}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["diverged_at_tick"] is None
    assert data["identical_prefix_length"] == 2
    assert data["differing_fields"] == {}

    # Different seeds should diverge at first tick
    run_c, _ = _create_run(ticks=2, seed=99)
    resp2 = client.get(f"/dashboard/compare/{run_a}/{run_c}")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["diverged_at_tick"] == 0
    assert data2["identical_prefix_length"] == 0
    assert isinstance(data2["differing_fields"], dict)
