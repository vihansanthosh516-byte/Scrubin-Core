'''Metrics service – expose simple deterministic metrics for a run.'''
from __future__ import annotations

from typing import List

from scrubin.control_plane.p9_debug import DebugFacade
from .dashboard_models import DashboardMetricSeries


class MetricsService:
    '''Service providing deterministic metrics derived from a stored run.'''

    def __init__(self, kernel):
        self.facade = DebugFacade(kernel)

    def get_metrics(self, run_id: str) -> List[DashboardMetricSeries]:
        # Retrieve artifact directly.
        artifact = self.facade._get_artifact(run_id)
        # Event count = length of timeline.
        timeline = getattr(artifact, "trajectory", [])
        event_counts = len(timeline)
        # Use the number of ticks (metadata ticks) if available.
        ticks = getattr(artifact, "metadata", {}).get("ticks") or len(timeline)
        return [
            DashboardMetricSeries(name="event_count", values=[event_counts]),
            DashboardMetricSeries(name="ticks", values=[ticks]),
        ]
