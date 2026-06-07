import pytest
from fastapi.testclient import TestClient

from scrubin.server.app import app
from scrubin.server.dependency_provider import get_kernel

client = TestClient(app)
kernel = get_kernel()

def _create_run(ticks=4, seed=5):
    artifact = kernel.run_simulation({"ticks": ticks, "seed": seed})
    return artifact.run_id, artifact

def test_metrics_endpoint():
    run_id, artifact = _create_run(ticks=3, seed=10)
    resp = client.get(f"/dashboard/metrics/{run_id}")
    assert resp.status_code == 200
    metrics = resp.json()
    # Expect two metric series: event_count and ticks
    names = {m["name"] for m in metrics}
    assert "event_count" in names
    assert "ticks" in names
    # Verify values match artifact metadata
    meta = getattr(artifact, "metadata", {})
    # Event count should be length of trajectory
    event_count = meta.get("ticks", 0)
    assert any(m["name"] == "event_count" and m["values"] == [event_count] for m in metrics)
    assert any(m["name"] == "ticks" and m["values"] == [event_count] for m in metrics)
