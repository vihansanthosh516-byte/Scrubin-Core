from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import uuid

@dataclass
class IRNode:
    id: str = field(default_factory=lambda: f"node-{uuid.uuid4().hex[:8]}")
    type: str = "GENERIC" # e.g. "VITALS_EVAL", "INTERVENTION", "MCTS_DECISION"
    payload: Dict[str, Any] = field(default_factory=dict)
    tick_offset: int = 0
    contract_id: str = "DEFAULT"

@dataclass
class IREdge:
    src: str
    dst: str
    condition: Optional[str] = None # e.g. "if SpO2 < 85"

@dataclass
class IRGraph:
    nodes: List[IRNode] = field(default_factory=list)
    edges: List[IREdge] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_node(self, node_id: str) -> Optional[IRNode]:
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None
