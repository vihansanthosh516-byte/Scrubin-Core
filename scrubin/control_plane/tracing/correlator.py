from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import uuid

@dataclass(frozen=True)
class TraceContext:
    trace_id: str = field(default_factory=lambda: f"tr-{uuid.uuid4().hex[:8]}")
    parent_id: Optional[str] = None
    session_id: str = "default"
    patient_id: Optional[str] = None

class TraceCorrelator:
    """
    Builds and traverses the distributed execution graph using trace identities.
    """
    def __init__(self):
        self._traces: Dict[str, List[str]] = {} # trace_id -> list of child_trace_ids

    def link(self, parent_id: Optional[str], child_id: str):
        if parent_id:
            if parent_id not in self._traces:
                self._traces[parent_id] = []
            self._traces[parent_id].append(child_id)

    def get_lineage(self, trace_id: str) -> List[str]:
        """
        Returns the full path from child back to root.
        """
        # In a real system, we'd have a back-pointer or query a database
        return [trace_id]
