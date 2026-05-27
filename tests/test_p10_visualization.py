import pytest

from scrubin.visualization import extract_phase_points, VisualizationService


def test_phase_space_extraction():
    traj = [
        {"a": 1, "b": 2},
        {"a": 2, "b": 3},
        {"a": 3, "b": 4},
    ]
    points = extract_phase_points(traj)
    assert len(points) == 3
    assert all("centroid" in p for p in points)


def test_view_structure():
    class DummyArtifact:
        run_id = "test"
        trajectory = [{"x": 1}]
        final_state = {"x": 1}
        metadata = {"hash": "abc"}

    # Minimal kernel stub – get_run returns the DummyArtifact instance
    kernel = type("K", (), {"get_run": lambda self, rid: DummyArtifact()})()
    viz = VisualizationService(kernel)
    view = viz.get_view("test")

    # The view must contain the three top‑level sections
    assert "run" in view
    assert "phase_space" in view
    assert "anomalies" in view

    # Verify that the phase space extraction matches our dummy trajectory
    assert isinstance(view["phase_space"], list)
    assert len(view["phase_space"]) == 1
    assert view["phase_space"][0]["centroid"] == 1
    # No adversary events in dummy data
    assert view["anomalies"] == []
