import json

from fastapi.testclient import TestClient
from scrubin.server.app import app

client = TestClient(app)


def _create_session(user_id: str, seed: int = 42, initial_tick: int = 0) -> str:
    """Create a session authenticated as ``user_id`` and return its id."""
    resp = client.post(
        "/session/create",
        json={"seed": seed, "initial_tick": initial_tick},
        headers={"Authorization": f"Bearer {user_id}"},
    )
    assert resp.status_code == 200, f"Create failed: {resp.text}"
    return resp.json()["session_id"]


def _action(session_id: str, user_id: str, action_type: str = "test_action"):
    resp = client.post(
        f"/session/{session_id}/action",
        json={"action_type": action_type, "parameters": {}, "timestamp": 0},
        headers={"Authorization": f"Bearer {user_id}"},
    )
    assert resp.status_code == 200, f"Action failed: {resp.text}"
    return resp.json()


def _state(session_id: str, user_id: str):
    resp = client.get(
        f"/session/{session_id}/state",
        headers={"Authorization": f"Bearer {user_id}"},
    )
    return resp


def _save(session_id: str, user_id: str):
    resp = client.post(
        f"/session/{session_id}/save",
        headers={"Authorization": f"Bearer {user_id}"},
    )
    return resp


def _load(session_id: str, user_id: str):
    resp = client.post(
        f"/session/{session_id}/load",
        headers={"Authorization": f"Bearer {user_id}"},
    )
    return resp


def _delete(session_id: str, user_id: str):
    resp = client.delete(
        f"/session/{session_id}",
        headers={"Authorization": f"Bearer {user_id}"},
    )
    return resp


def _list(user_id: str):
    resp = client.get(
        "/sessions",
        headers={"Authorization": f"Bearer {user_id}"},
    )
    return resp


def test_user_cannot_access_other_session():
    user_a = "user_a"
    user_b = "user_b"
    sess = _create_session(user_a)
    resp = _state(sess, user_b)
    assert resp.status_code == 403
    err = resp.json()
    assert "message" in err


def test_user_cannot_save_other_session():
    user_a = "user_a"
    user_b = "user_b"
    sess = _create_session(user_a)
    resp = _save(sess, user_b)
    assert resp.status_code == 403
    err = resp.json()
    assert "message" in err


def test_user_cannot_load_other_session():
    user_a = "user_a"
    user_b = "user_b"
    sess = _create_session(user_a)
    # Ensure there is something to load (save first as owner)
    _save(sess, user_a)
    resp = _load(sess, user_b)
    assert resp.status_code == 403
    err = resp.json()
    assert "message" in err


def test_user_cannot_delete_other_session():
    user_a = "user_a"
    user_b = "user_b"
    sess = _create_session(user_a)
    resp = _delete(sess, user_b)
    assert resp.status_code == 403
    err = resp.json()
    assert "message" in err


def test_session_owner_persists_after_save_load():
    user = "owner_user"
    sess = _create_session(user)
    save_resp = _save(sess, user)
    assert save_resp.status_code == 200
    meta_save = save_resp.json()["metadata"]
    assert meta_save["owner_user_id"] == user

    load_resp = _load(sess, user)
    assert load_resp.status_code == 200
    meta_load = load_resp.json()["metadata"]
    assert meta_load["owner_user_id"] == user


def test_list_sessions_returns_only_owned_sessions():
    user_a = "user_a"
    user_b = "user_b"
    sess_a = _create_session(user_a)
    sess_b = _create_session(user_b)
    list_a = _list(user_a).json()
    list_b = _list(user_b).json()
    assert sess_a in list_a
    assert sess_b not in list_a
    assert sess_b in list_b
    assert sess_a not in list_b


def test_auth_metadata_does_not_modify_worldstate():
    seed = 123
    user_a = "user_a"
    user_b = "user_b"
    sess_a = _create_session(user_a, seed=seed)
    sess_b = _create_session(user_b, seed=seed)
    # Perform identical actions on each session
    for _ in range(5):
        _action(sess_a, user_a)
        _action(sess_b, user_b)
    state_a = _state(sess_a, user_a).json()
    state_b = _state(sess_b, user_b).json()
    # The world state sections must be identical (ignoring owner metadata which is not part of WorldState)
    assert state_a["world_tick"] == state_b["world_tick"]
    assert state_a["timeline_events"] == state_b["timeline_events"]
    # Full serialized world state equality (deep compare)
    assert json.dumps(state_a["current_world_state"], sort_keys=True) == json.dumps(state_b["current_world_state"], sort_keys=True)


def test_authentication_preserves_replay_determinism():
    user = "determinism_user"
    # Continuous run (40 actions)
    sess_a = _create_session(user, seed=99)
    for _ in range(40):
        _action(sess_a, user)
    state_a = _state(sess_a, user).json()

    # Branch with save/load after 20 actions
    sess_b = _create_session(user, seed=99)
    for _ in range(20):
        _action(sess_b, user)
    _save(sess_b, user)
    _load(sess_b, user)
    for _ in range(20):
        _action(sess_b, user)
    state_b = _state(sess_b, user).json()

    # Final states must be identical
    assert state_a == state_b
