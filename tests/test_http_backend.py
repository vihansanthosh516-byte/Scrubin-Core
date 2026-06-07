import json

from fastapi.testclient import TestClient
from scrubin.server.app import app

client = TestClient(app)

def _create_session(seed: int = 42, initial_tick: int = 0):
    response = client.post("/session/create", json={"seed": seed, "initial_tick": initial_tick})
    assert response.status_code == 200
    data = response.json()
    return data["session_id"], data["initial_world_state"]

def test_session_lifecycle_and_errors():
    # Create a new session.
    session_id, init_state = _create_session()
    assert init_state["tick"] == 0

    # Retrieve state.
    resp = client.get(f"/session/{session_id}/state")
    assert resp.status_code == 200
    state = resp.json()
    assert state["world_tick"] == 0

    # Perform one action.
    action_resp = client.post(
        f"/session/{session_id}/action",
        json={"action_type": "test_action", "parameters": {}, "timestamp": 0},
    )
    assert action_resp.status_code == 200
    action_data = action_resp.json()
    assert action_data["world_tick"] == 1
    assert len(action_data["timeline_events"]) == 1

    # Save the session.
    save_resp = client.post(f"/session/{session_id}/save")
    assert save_resp.status_code == 200
    save_data = save_resp.json()
    assert "metadata" in save_data
    meta = save_data["metadata"]
    assert meta["session_id"] == session_id
    assert meta["world_hash"]

    # Apply another action (tick becomes 2).
    client.post(
        f"/session/{session_id}/action",
        json={"action_type": "test_action2", "parameters": {}, "timestamp": 0},
    )
    # Load the previously saved snapshot (should revert to tick 1).
    load_resp = client.post(f"/session/{session_id}/load")
    assert load_resp.status_code == 200
    loaded = load_resp.json()
    state_after_load = loaded["state"]
    assert state_after_load["world_tick"] == 1

    # Delete the session.
    del_resp = client.delete(f"/session/{session_id}")
    assert del_resp.status_code == 200
    # Subsequent access fails.
    resp = client.get(f"/session/{session_id}/state")
    assert resp.status_code == 404

def test_list_and_invalid_session():
    # Create two sessions and persist them.
    sid1, _ = _create_session(seed=1)
    client.post(f"/session/{sid1}/save")
    sid2, _ = _create_session(seed=2)
    client.post(f"/session/{sid2}/save")
    list_resp = client.get("/sessions")
    assert list_resp.status_code == 200
    ids = list_resp.json()
    assert sorted(ids) == sorted([sid1, sid2])
    # Delete one and verify list updates.
    client.delete(f"/session/{sid1}")
    ids_after = client.get("/sessions").json()
    assert sid1 not in ids_after
    assert sid2 in ids_after
    # Invalid session handling.
    bad_resp = client.get("/session/nonexistent/state")
    assert bad_resp.status_code == 404
    err = bad_resp.json()
    assert "message" in err

def test_replay_consistency_via_http():
    # Continuous run: 40 actions.
    sess_a, _ = _create_session(seed=99)
    for _ in range(40):
        client.post(
            f"/session/{sess_a}/action",
            json={"action_type": "tick", "parameters": {}, "timestamp": 0},
        )
    state_a = client.get(f"/session/{sess_a}/state").json()

    # Branch B: 20 actions, save, load, then 20 actions.
    sess_b, _ = _create_session(seed=99)
    for _ in range(20):
        client.post(
            f"/session/{sess_b}/action",
            json={"action_type": "tick", "parameters": {}, "timestamp": 0},
        )
    client.post(f"/session/{sess_b}/save")
    client.post(f"/session/{sess_b}/load")
    for _ in range(20):
        client.post(
            f"/session/{sess_b}/action",
            json={"action_type": "tick", "parameters": {}, "timestamp": 0},
        )
    state_b = client.get(f"/session/{sess_b}/state").json()

    # The resulting states must be identical.
    assert state_a == state_b
