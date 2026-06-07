import pytest
from dataclasses import FrozenInstanceError

from scrubin.dashboard.dashboard_models import (
    DashboardRunSummary,
    DashboardReplayFrame,
    DashboardMetricSeries,
    DashboardKnowledgeGraph,
    DashboardSnapshot,
    DashboardComparison,
)

def test_models_are_frozen():
    # Run summary
    summary = DashboardRunSummary(run_id="run1", seed=42, ticks=5, hash="abcd")
    with pytest.raises(FrozenInstanceError):
        summary.run_id = "run2"

    # Replay frame
    frame = DashboardReplayFrame(tick=0, state_hash="h", diff_from_previous={})
    with pytest.raises(FrozenInstanceError):
        frame.tick = 1

    # Metric series
    series = DashboardMetricSeries(name="event", values=[1, 2, 3])
    with pytest.raises(FrozenInstanceError):
        series.name = "other"

    # Knowledge graph
    kg = DashboardKnowledgeGraph(nodes=[], edges=[])
    with pytest.raises(FrozenInstanceError):
        kg.nodes = []

    # Snapshot
    snap = DashboardSnapshot(world_state={"tick": 0}, diff_from_previous={})
    with pytest.raises(FrozenInstanceError):
        snap.world_state = {"tick": 1}

    # Comparison
    cmp = DashboardComparison(diverged_at_tick=None, identical_prefix_length=5, differing_fields={})
    with pytest.raises(FrozenInstanceError):
        cmp.identical_prefix_length = 6
