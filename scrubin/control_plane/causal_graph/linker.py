from typing import List, Optional
from scrubin.control_plane.causal_graph.engine import CausalExecutionGraph, EdgeType
from scrubin.control_plane.semantic_events.models import SemanticEvent

class CausalLinker:
    """
    Applies deterministic rules to infer causal edges between semantic events.
    """
    def __init__(self, graph: CausalExecutionGraph):
        self.graph = graph

    def link_event(self, new_event: SemanticEvent, recent_events: List[SemanticEvent]):
        """
        Heuristic-based linkage logic.
        """
        # Rule 1: Explicit Parent Tracing
        if new_event.parent_trace_id:
            # Find the event that spawned this trace
            for prev in reversed(recent_events):
                if prev.trace_id == new_event.parent_trace_id:
                    self.graph.add_edge(prev.event_id, new_event.event_id, EdgeType.TRIGGERED_BY)
                    break

        # Rule 2: Clinical Deterioration -> Planner Action
        if new_event.category == "PLANNER":
            for prev in reversed(recent_events):
                if prev.category == "CLINICAL" and prev.topic == "patient.vitals":
                    # If vitals were abnormal, the planner action responds to it
                    if new_event.timestamp_tick >= prev.timestamp_tick:
                        if prev.payload.get("spo2", 100) < 90 or prev.payload.get("hr", 80) > 120:
                            self.graph.add_edge(prev.event_id, new_event.event_id, EdgeType.RESPONDS_TO)
                            break

        # Rule 3: Planner Action -> Clinical Change
        if new_event.category == "CLINICAL":
            for prev in reversed(recent_events):
                if prev.category == "PLANNER":
                    # Assume clinical changes shortly after planner actions are caused by them
                    delta = new_event.timestamp_tick - prev.timestamp_tick
                    if 0 <= delta <= 5:
                        self.graph.add_edge(prev.event_id, new_event.event_id, EdgeType.CAUSED_BY)
                        break

        # Rule 4: Distributed Conflict
        if new_event.topic == "verification.divergence":
            for prev in reversed(recent_events):
                if prev.topic == new_event.topic and prev.event_id != new_event.event_id:
                    self.graph.add_edge(prev.event_id, new_event.event_id, EdgeType.CONFLICTS_WITH)
