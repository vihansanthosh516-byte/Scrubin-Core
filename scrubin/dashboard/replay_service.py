'''Replay service exposing deterministic frames for a run.

This thin wrapper uses the P.9 DebugFacade to obtain ReplayFrame objects
and converts them to the immutable DashboardReplayFrame dataclasses defined
in dashboard_models.
'''
from __future__ import annotations

from typing import List, Optional

from scrubin.control_plane.p9_debug import DebugFacade
from .dashboard_models import DashboardReplayFrame


class ReplayService:
    '''Service providing deterministic replay frames for a stored run.'''

    def __init__(self, kernel):
        self.facade = DebugFacade(kernel)

    def get_frames(self, run_id: str, ticks: Optional[int] = None) -> List[DashboardReplayFrame]:
        '''Return a list of DashboardReplayFrame for the given run.

        Parameters
        ----------
        run_id: str
            Identifier of the stored run.
        ticks: int | None
            Number of ticks to include. None returns the full trajectory.
        '''
        frames = self.facade.replay_inspect(run_id, ticks=ticks)
        return [
            DashboardReplayFrame(
                tick=f.tick,
                state_hash=f.state_hash,
                diff_from_previous=f.diff_from_previous,
            )
            for f in frames
        ]
