from typing import Any, List
from scrubin.control_plane.causal_graph.engine import CausalExecutionGraph
from scrubin.optimization.debug.trace_schema import EpisodeStepTrace

class CausalEpisodeLinker:
    """
    Connects RL steps to Causal Execution Graph (CEG) nodes.
    Turns RL actions into navigable causal anchor points.
    """
    def link(self, step_trace: EpisodeStepTrace, ceg: CausalExecutionGraph) -> List[str]:
        """
        Maps RL step to specific simulation events and their upstream causes.
        """
        linked_ids = []
        
        # 1. Map by Tick and Session
        # In a real system, we'd use high-precision event mapping
        for event_id, event in ceg.nodes.items():
            if event.timestamp_tick == step_trace.tick:
                linked_ids.append(event_id)
                
                # 2. Add upstream causes for forensics
                causes = ceg.get_upstream_causes(event_id, depth=2)
                linked_ids.extend([c.event_id for c in causes])
                
        return list(set(linked_ids)) # Unique links
