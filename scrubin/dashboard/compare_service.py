'''Comparison service – deterministic diff of two runs.

Uses the P.9 RunDiffEngine via DebugFacade and wraps the result in the
immutable DashboardComparison dataclass.
'''
from __future__ import annotations

from scrubin.control_plane.p9_debug import DebugFacade
from .dashboard_models import DashboardComparison


class CompareService:
    '''Service to compare two execution artifacts.'''

    def __init__(self, kernel):
        self.facade = DebugFacade(kernel)

    def compare(self, run_a: str, run_b: str) -> DashboardComparison:
        diff = self.facade.run_diff(run_a, run_b)
        return DashboardComparison(
            diverged_at_tick=diff.diverged_at_tick,
            identical_prefix_length=diff.identical_prefix_length,
            differing_fields=diff.differing_fields,
        )
