from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class InterAgentEdge:
    from_agent: str
    to_agent: str
    event_id: str
    impact_type: str # e.g. "RESOURCE_CONTENTION", "STATE_MODIFICATION"

class InterAgentCEG:
    """
    Extends the Causal Execution Graph to track cross-agent interference.
    Maps how actions of Agent A influence the constraints or outcomes of Agent B.
    """
    def __init__(self):
        self.edges: List[InterAgentEdge] = []

    def record_interference(self, from_agent: str, to_agent: str, event_id: str, impact: str):
        self.edges.append(InterAgentEdge(from_agent, to_agent, event_id, impact))

    def get_interference_tree(self, agent_id: str) -> List[InterAgentEdge]:
        return [e for e in self.edges if e.to_agent == agent_id]
