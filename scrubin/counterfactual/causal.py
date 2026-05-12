from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class CausalNode:
    node_id: str
    node_type: str
    label: str
    value: float = 0.0


@dataclass
class CausalEdge:
    source: str
    target: str
    edge_type: str
    weight: float = 1.0


@dataclass
class InterventionNode:
    action: str
    tick: int
    targets: List[str] = field(default_factory=list)
    effect_magnitude: float = 0.0


class CausalInterventionGraph:
    def __init__(self):
        self._nodes: Dict[str, CausalNode] = {}
        self._edges: List[CausalEdge] = []
        self._interventions: List[InterventionNode] = []

    def add_node(self, node: CausalNode) -> None:
        self._nodes[node.node_id] = node

    def add_edge(self, edge: CausalEdge) -> None:
        self._edges.append(edge)

    def add_intervention(self, intervention: InterventionNode) -> None:
        self._interventions.append(intervention)

    @property
    def nodes(self) -> Dict[str, CausalNode]:
        return dict(self._nodes)

    @property
    def edges(self) -> List[CausalEdge]:
        return list(self._edges)

    @property
    def interventions(self) -> List[InterventionNode]:
        return list(self._interventions)

    def ancestors(self, node_id: str) -> List[str]:
        result = []
        visited = set()
        queue = [node_id]
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            for edge in self._edges:
                if edge.target == current and edge.source not in visited:
                    result.append(edge.source)
                    queue.append(edge.source)
        return result

    def descendants(self, node_id: str) -> List[str]:
        result = []
        visited = set()
        queue = [node_id]
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            for edge in self._edges:
                if edge.source == current and edge.target not in visited:
                    result.append(edge.target)
                    queue.append(edge.target)
        return result

    def effect_of(self, action: str) -> List[CausalEdge]:
        return [e for e in self._edges if e.source == action or e.source.startswith(f"action:{action}")]

    def to_dict(self) -> dict:
        return {
            "nodes": {k: {"type": v.node_type, "label": v.label, "value": v.value} for k, v in self._nodes.items()},
            "edges": [{"source": e.source, "target": e.target, "type": e.edge_type, "weight": e.weight} for e in self._edges],
            "interventions": [
                {"action": i.action, "tick": i.tick, "targets": i.targets, "magnitude": i.effect_magnitude}
                for i in self._interventions
            ],
        }


def build_causal_graph_from_world(world_dict: dict) -> CausalInterventionGraph:
    graph = CausalInterventionGraph()
    physiology = world_dict.get("physiology", {})
    vitals = physiology.get("vitals", {})
    for vital_name, value in vitals.items():
        graph.add_node(CausalNode(node_id=f"vital:{vital_name}", node_type="vital", label=vital_name, value=value))
    organs = world_dict.get("organ_state", {})
    for organ_name, organ_data in organs.items():
        if isinstance(organ_data, dict):
            health = organ_data.get("health", 0.0)
        else:
            health = 0.0
        graph.add_node(CausalNode(node_id=f"organ:{organ_name}", node_type="organ", label=organ_name, value=health))
    organ_names = [n.node_id for n in graph._nodes.values() if n.node_type == "organ"]
    vital_names = [n.node_id for n in graph._nodes.values() if n.node_type == "vital"]
    cascade_edges = [
        ("organ:cardiovascular", "organ:renal"),
        ("organ:cardiovascular", "organ:respiratory"),
    ]
    for src, dst in cascade_edges:
        if src in graph._nodes and dst in graph._nodes:
            graph.add_edge(CausalEdge(source=src, target=dst, edge_type="cascade", weight=0.5))
    vital_organ_links = [
        ("vital:spo2", "organ:respiratory"),
        ("vital:bp_systolic", "organ:cardiovascular"),
        ("vital:heart_rate", "organ:cardiovascular"),
    ]
    for src, dst in vital_organ_links:
        if src in graph._nodes and dst in graph._nodes:
            graph.add_edge(CausalEdge(source=src, target=dst, edge_type="influence", weight=0.3))
    return graph
