'''Graph service – deterministic causal trace reconstruction.'''
from __future__ import annotations

from scrubin.control_plane.p9_debug import DebugFacade
from scrubin.debug.causal_trace_engine import CausalTraceEngine


class GraphService:
    '''Service to produce causal trace graphs for a specific event.'''

    def __init__(self, kernel):
        self.facade = DebugFacade(kernel)
        self.engine = CausalTraceEngine()

    def get_causal_trace(self, run_id: str, tick: int, description: str):
        artifact = self.facade._get_artifact(run_id)
        return self.engine.trace(artifact, tick, description)
