from typing import List, Dict, Any, Callable
from scrubin.control_plane.semantic_events.models import SemanticEvent

class SemanticQueryEngine:
    """
    Executes complex semantic graph queries over execution history.
    """
    def __init__(self, event_history: List[SemanticEvent]):
        self.history = event_history

    def query(self, filter_fn: Callable[[SemanticEvent], bool]) -> List[SemanticEvent]:
        return [ev for ev in self.history if filter_fn(ev)]

    def find_causal_chains(self, trace_id: str) -> List[SemanticEvent]:
        """
        Retrieves all events linked to a specific causal root.
        """
        return [ev for ev in self.history if ev.trace_id == trace_id or ev.parent_trace_id == trace_id]

    def aggregate_by_category(self) -> Dict[str, int]:
        counts = {}
        for ev in self.history:
            counts[ev.category] = counts.get(ev.category, 0) + 1
        return counts
