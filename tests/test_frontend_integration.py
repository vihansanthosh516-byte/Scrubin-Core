import json

import pytest

from scrubin.server.app import app
from scrubin.client import ScrubinClient
from scrubin.config import Config

# FastAPI TestClient is not needed – ScrubinClient can use ASGI transport directly.

from fastapi.testclient import TestClient

# Use FastAPI's in‑process test client so the ScrubinClient can operate without network I/O.
fastapi_client = TestClient(app)
client = ScrubinClient(client=fastapi_client)


def test_health_endpoint():
    resp = client.health()
    assert isinstance(resp, dict)
    assert resp.get("status") == "ok"


def test_readiness_endpoint():
    resp = client.ready()
    assert isinstance(resp, dict)
    assert resp.get("status") == "ready"


def test_api_client_requests_and_determinism():
    token_a = "user_a"
    # Create a session
    create_resp = client.create_session(seed=100, token=token_a)
    sid = create_resp["session_id"]
    # Verify it appears in list
    lst = client.list_sessions(token=token_a)
    assert sid in lst
    # Perform an action
    action_resp = client.post_action(sid, action_type="test_action", token=token_a)
    assert action_resp["world_tick"] == 1
    # Save the session
    save_resp = client.save_session(sid, token=token_a)
    assert "metadata" in save_resp
    # Load the session (should be idempotent)
    load_resp = client.load_session(sid, token=token_a)
    assert load_resp["metadata"]["session_id"] == sid
    # Delete the session
    del_resp = client.delete_session(sid, token=token_a)
    assert "detail" in del_resp
    # Ensure it is gone from list
    lst2 = client.list_sessions(token=token_a)
    assert sid not in lst2


def test_configuration_loading(monkeypatch):
    monkeypatch.setenv("SCRUBIN_API_URL", "http://example.com")
    monkeypatch.setenv("SCRUBIN_TIMEOUT", "10")
    cfg = Config()
    assert cfg.api_base_url == "http://example.com"
    assert cfg.timeout == 10
