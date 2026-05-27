import pytest
from fastapi.testclient import TestClient

from scrubin.api.run_api import app

client = TestClient(app)

def test_run_and_get_and_replay():
    # Submit a run with deterministic configuration
    config = {"ticks": 5, "seed": 123, "initial_state": {}}
    resp = client.post("/run", json=config)
    assert resp.status_code == 200
    data = resp.json()
    assert "run_id" in data and isinstance(data["run_id"], str)
    assert "hash" in data and isinstance(data["hash"], str)
    assert data["ticks"] == 5

    run_id = data["run_id"]

    # Retrieve the full artifact
    resp_get = client.get(f"/run/{run_id}")
    assert resp_get.status_code == 200
    artifact = resp_get.json()
    assert artifact["run_id"] == run_id
    assert artifact["metadata"]["ticks"] == 5
    assert artifact["metadata"]["hash"] == data["hash"]

    # Replay endpoint should return trajectory and final state
    resp_replay = client.get(f"/replay/{run_id}")
    assert resp_replay.status_code == 200
    replay_data = resp_replay.json()
    assert "trajectory" in replay_data and isinstance(replay_data["trajectory"], list)
    assert "final_state" in replay_data
    # Trajectory length must match ticks
    assert len(replay_data["trajectory"]) == 5
    # Final state must be the last element of the trajectory
    assert replay_data["final_state"] == replay_data["trajectory"][-1]

def test_repeat_runs_same_seed():
    config = {"ticks": 4, "seed": 999, "initial_state": {}}
    resp1 = client.post("/run", json=config)
    resp2 = client.post("/run", json=config)
    assert resp1.status_code == 200 and resp2.status_code == 200
    data1 = resp1.json()
    data2 = resp2.json()
    # Different run IDs for each submission
    assert data1["run_id"] != data2["run_id"]
    # Deterministic hash must be identical
    assert data1["hash"] == data2["hash"]
    assert data1["ticks"] == data2["ticks"] == 4
