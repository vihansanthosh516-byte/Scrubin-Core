from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any
from scrubin.control_plane.semantic_events.models import SemanticEvent

class EdgeType(Enum):
    CAUSED_BY = "caused_by"
    TRIGGERED_BY = "triggered_by"
    MODIFIES = "modifies"
    RESPONDS_TO = "responds_to"
    CONFLICTS_WITH = "conflicts_with"

@dataclass(frozen=True)
class CausalEdge:
    source_id: str
    target_id: str
    edge_type: EdgeType
    metadata: Dict[str, Any] = field(default_factory=dict)

class CausalExecutionGraph:
    """
    Maintains a navigable cause-effect structure of all execution events.
    """
    def __init__(self):
        self.nodes: Dict[str, SemanticEvent] = {}
        self.edges: List[CausalEdge] = []
        self._adjacency_out: Dict[str, List[CausalEdge]] = {}
        self._adjacency_in: Dict[str, List[CausalEdge]] = {}

    def add_event(self, event: SemanticEvent):
        self.nodes[event.event_id] = event
        if event.event_id not in self._adjacency_out:
            self._adjacency_out[event.event_id] = []
        if event.event_id not in self._adjacency_in:
            self._adjacency_in[event.event_id] = []

    def add_edge(self, source_id: str, target_id: str, edge_type: EdgeType, metadata: Dict[str, Any] = None):
        edge = CausalEdge(source_id, target_id, edge_type, metadata or {})
        self.edges.append(edge)
        self._adjacency_out[source_id].append(edge)
        self._adjacency_in[target_id].append(edge)

    def get_upstream_causes(self, event_id: str, depth: int = 5) -> List[SemanticEvent]:
        """
        Traverses backwards (inbound edges) to find root causes.
        """
        causes = []
        visited = {event_id}
        queue = [(event_id, 0)]
        
        while queue:
            current_id, d = queue.pop(0)
            if d >= depth: continue
            
            for edge in self._adjacency_in.get(current_id, []):
                if edge.source_id not in visited:
                    visited.add(edge.source_id)
                    causes.append(self.nodes[edge.source_id])
                    queue.append((edge.source_id, d + 1))
        return causes

    def get_downstream_effects(self, event_id: str, depth: int = 5) -> List[SemanticEvent]:
        """
        Traverses forwards (outbound edges) to find cascading effects.
        """
        effects = []
        visited = {event_id}
        queue = [(event_id, 0)]
        
        while queue:
            current_id, d = queue.pop(0)
            if d >= depth: continue
            
            for edge in self._adjacency_out.get(current_id, []):
                if edge.target_id not in visited:
                    visited.add(edge.target_id)
                    effects.append(self.nodes[edge.target_id])
                    queue.append((edge.target_id, d + 1))
        return effects
