# Tests for the new procedure catalog endpoint and procedure‑aware session start

from fastapi.testclient import TestClient
from scrubin.api.server import app

client = TestClient(app)


def test_get_procedures_returns_appendectomy():
    resp = client.get("/procedures")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert any(entry["id"] == "appendectomy" for entry in data)
    name = next(entry["name"] for entry in data if entry["id"] == "appendectomy")
    assert "Appendectomy" in name


def test_start_session_with_procedure_id():
    resp = client.post(
        "/session/start",
        json={
            "seed": 42,
            "profile": "default",
            "patient_profile": "standard",
            "mode": "interactive",
            "procedure_id": "appendectomy",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    sid = data["session_id"]
    opts_resp = client.get("/session/options", params={"session_id": sid})
    opts = opts_resp.json()["options"]
    # Options may be empty at start (generic monitor/wait are filtered out when no complication)
    assert isinstance(opts, list)
