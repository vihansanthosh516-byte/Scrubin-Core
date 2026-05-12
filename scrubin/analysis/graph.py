from dataclasses import dataclass, field
from typing import Dict, List, Any


@dataclass
class Node:
    id: int
    type: str
    tick: int
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Edge:
    source: int
    target: int
    reason: str


@dataclass
class CausalityGraph:
    nodes: Dict[int, Node] = field(default_factory=dict)
    edges: List[Edge] = field(default_factory=list)
    _next_id: int = field(default=100000, repr=False)

    def add_node(self, node: Node):
        self.nodes[node.id] = node

    def add_edge(self, source: int, target: int, reason: str):
        self.edges.append(Edge(source, target, reason))

    def add_fusion_node(self, tick: int, label: str, inputs: List[str] = None, policy: str = None, deterministic_key: str = None, explanation: str = None) -> int:
        fid = self._next_id
        self._next_id += 1
        payload = {"fusion": True}
        if inputs is not None:
            payload["inputs"] = inputs
        if policy is not None:
            payload["policy"] = policy
        if deterministic_key is not None:
            payload["deterministic_key"] = deterministic_key
        if explanation is not None:
            payload["explanation"] = explanation
        self.nodes[fid] = Node(
            id=fid,
            type=label,
            tick=tick,
            payload=payload,
        )
        return fid
