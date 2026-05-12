from typing import Dict, Any, List, Optional
from scrubin.control_plane.replay.engine import ReplayEngine
from scrubin.control_plane.replay.state import ReplayState

class ReplayExecutor:
    """
    Isolated interface for executing deterministic replays from the kernel.
    Ensures zero mutation of live system state.
    """
    def __init__(self, causal_graph: Any):
        self.engine = ReplayEngine(causal_graph)

    def reconstruct_session(self, session_id: str) -> Dict[str, Any]:
        """
        Public entry point for full session reconstruction.
        """
        return self.engine.replay_trace(session_id)

    def jump_to_event(self, session_id: str, event_id: str) -> Optional[ReplayState]:
        """
        Enables jump-debugging by retrieving the snapshot at a specific event.
        """
        result = self.reconstruct_session(session_id)
        return result["snapshots"].get(event_id)
