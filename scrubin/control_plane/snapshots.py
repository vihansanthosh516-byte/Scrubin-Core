from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import uuid
import time

@dataclass
class Snapshot:
    session_id: str
    tick: int
    state_blob: Dict[str, Any] # Deterministic simulation state
    id: str = field(default_factory=lambda: f"snap-{uuid.uuid4().hex[:8]}")
    timestamp: float = field(default_factory=time.time)

class SnapshotManager:
    """
    Manages state snapshots for reproducibility and counterfactuals.
    """
    def __init__(self):
        self.snapshots: Dict[str, Snapshot] = {}

    def capture(self, session_id: str, tick: int, state: Dict[str, Any]) -> str:
        snap = Snapshot(session_id=session_id, tick=tick, state_blob=state)
        self.snapshots[snap.id] = snap
        return snap.id

    def get_snapshot(self, snapshot_id: str) -> Optional[Snapshot]:
        return self.snapshots.get(snapshot_id)

    def list_for_session(self, session_id: str) -> List[Snapshot]:
        return [s for s in self.snapshots.values() if s.session_id == session_id]
