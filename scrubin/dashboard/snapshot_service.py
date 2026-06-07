'''Snapshot service – deterministic inspection of world snapshots.'''
from __future__ import annotations

from scrubin.control_plane.p9_debug import DebugFacade
from .dashboard_models import DashboardSnapshot
from scrubin.debug.snapshot_viewer import SnapshotViewer


class SnapshotService:
    '''Service to retrieve and diff snapshots for a run.'''

    def __init__(self, kernel):
        self.facade = DebugFacade(kernel)
        self.viewer = SnapshotViewer()

    def get_final_snapshot(self, run_id: str) -> DashboardSnapshot:
        artifact = self.facade._get_artifact(run_id)
        final_state = getattr(artifact, "final_state", None) or (artifact.trajectory[-1] if artifact.trajectory else None)
        if final_state is None:
            raise ValueError("Run has no final state")
        # No diff for final snapshot.
        return DashboardSnapshot(world_state=final_state, diff_from_previous={})

    def diff_with_previous(self, run_id: str) -> DashboardSnapshot:
        artifact = self.facade._get_artifact(run_id)
        trajectory = getattr(artifact, "trajectory", [])
        if len(trajectory) < 2:
            raise ValueError("Not enough snapshots to compute diff")
        prev_state = trajectory[-2]
        cur_state = trajectory[-1]
        diff = self.viewer.diff(prev_state, cur_state)
        return DashboardSnapshot(world_state=cur_state, diff_from_previous=diff)
