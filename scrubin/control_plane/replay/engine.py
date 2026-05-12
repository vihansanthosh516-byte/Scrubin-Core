from typing import List, Dict, Any, Optional, Set
from scrubin.control_plane.causal_graph.engine import CausalExecutionGraph, EdgeType
from scrubin.control_plane.semantic_events.models import SemanticEvent
from scrubin.control_plane.replay.state import ReplayState, StateMutator
from scrubin.control_plane.contracts.determinism import DeterminismContract

class ReplayEngine:
    """
    Deterministic state machine driven by a causally sorted event DAG.
    """
    def __init__(self, causal_graph: CausalExecutionGraph):
        self.graph = causal_graph
        self.mutator = StateMutator()

    def replay_trace(self, trace_id: str, initial_state: Optional[ReplayState] = None) -> Dict[str, Any]:
        """
        Reconstructs state for a specific trace by applying events in causal order.
        """
        # 1. Filter events belonging to this trace
        trace_events = [ev for ev in self.graph.nodes.values() if ev.trace_id == trace_id or ev.session_id == trace_id]
        
        # 2. Perform Topological Sort based on Causal Edges
        ordered_events = self._topological_sort(trace_events)
        
        # 3. Deterministic Application Loop
        current_state = initial_state or ReplayState()
        snapshots = {}
        
        for event in ordered_events:
            current_state = self.mutator.apply(event, current_state)
            snapshots[event.event_id] = current_state # Already copied by mutator
            
        return {
            "final_state": current_state,
            "snapshots": snapshots,
            "execution_order": [e.event_id for e in ordered_events]
        }

    def _topological_sort(self, events: List[SemanticEvent]) -> List[SemanticEvent]:
        """
        Kahn's algorithm or similar to ensure causal parent events are applied first.
        """
        event_ids = {e.event_id for e in events}
        in_degree = {e.event_id: 0 for e in events}
        adj = {e.event_id: [] for e in events}
        
        # Build dependency graph from CEG edges
        for edge in self.graph.edges:
            if edge.source_id in event_ids and edge.target_id in event_ids:
                adj[edge.source_id].append(edge.target_id)
                in_degree[edge.target_id] += 1
                
        # Topological Sort
        queue = [eid for eid, degree in in_degree.items() if degree == 0]
        # Secondary sort using standardized contract key to stabilize ties
        queue.sort(key=lambda eid: DeterminismContract.get_sort_key(self.graph.nodes[eid]))
        
        ordered_ids = []
        while queue:
            u = queue.pop(0)
            ordered_ids.append(u)
            
            for v in adj[u]:
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    queue.append(v)
                    # Re-sort queue to maintain deterministic tie-breaking
                    queue.sort(key=lambda eid: DeterminismContract.get_sort_key(self.graph.nodes[eid]))
                    
        # If cycles exist or events are missing (incomplete DAG), fallback to temporal order
        if len(ordered_ids) != len(events):
            print("[REPLAY] WARNING: Causal DAG is incomplete or cyclic. Falling back to temporal order.")
            return sorted(events, key=lambda e: e.timestamp_tick)
            
        return [self.graph.nodes[eid] for eid in ordered_ids]
