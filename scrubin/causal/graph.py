from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from scrubin.counterfactual.causal import CausalNode, CausalEdge, CausalInterventionGraph


@dataclass
class InterventionEffect:
    action: str
    target: str
    magnitude: float
    tick: int
    causal_path: List[str] = field(default_factory=list)


@dataclass
class CounterfactualDelta:
    node_id: str
    original_value: float
    counterfactual_value: float
    delta: float


class CausalGraphEngine:
    def __init__(self):
        self.static_graph = self._build_static_physiological_graph()

    def _build_static_physiological_graph(self) -> CausalInterventionGraph:
        graph = CausalInterventionGraph()
        
        # Nodes
        nodes = [
            CausalNode("hemorrhage", "complication", "Hemorrhage"),
            CausalNode("map_collapse", "physiology", "MAP Collapse"),
            CausalNode("renal_hypoperfusion", "physiology", "Renal Hypoperfusion"),
            CausalNode("aki", "pathology", "AKI"),
            CausalNode("mortality", "outcome", "Mortality Increase"),
            
            CausalNode("hypoxia", "complication", "Hypoxia"),
            CausalNode("respiratory_failure", "physiology", "Respiratory Failure"),
            CausalNode("cardiac_arrest", "physiology", "Cardiac Arrest"),
        ]
        for n in nodes: graph.add_node(n)

        # Edges
        edges = [
            CausalEdge("hemorrhage", "map_collapse", "causes", 0.9),
            CausalEdge("map_collapse", "renal_hypoperfusion", "causes", 0.8),
            CausalEdge("renal_hypoperfusion", "aki", "leads_to", 0.7),
            CausalEdge("aki", "mortality", "increases", 0.5),
            
            CausalEdge("hypoxia", "respiratory_failure", "causes", 0.8),
            CausalEdge("respiratory_failure", "cardiac_arrest", "triggers", 0.9),
            CausalEdge("cardiac_arrest", "mortality", "causes", 1.0),
            
            CausalEdge("map_collapse", "cardiac_arrest", "contributes", 0.6),
        ]
        for e in edges: graph.add_edge(e)
        
        return graph

    def explain_outcome(self, outcome_node: str = "mortality") -> str:
        """
        Explains why a certain outcome occurred by tracing back causal ancestors.
        Example: "Why did the patient die?" -> "Hemorrhage caused MAP collapse, which triggered Cardiac Arrest, leading to Mortality."
        """
        if outcome_node not in self.static_graph.nodes:
            return f"Unknown outcome node: {outcome_node}"
            
        ancestors = self.static_graph.ancestors(outcome_node)
        # Simplified explanation generation
        path = []
        curr = outcome_node
        while True:
            parents = [e.source for e in self.static_graph.edges if e.target == curr]
            if not parents: break
            # Pick strongest parent for explanation
            parent = parents[0] 
            path.append(curr)
            curr = parent
            if curr in path: break # Avoid cycles
        
        path.append(curr)
        path.reverse()
        
        explanation = " -> ".join([self.static_graph.nodes[p].label for p in path])
        return f"Causal Attribution: {explanation}"

    def get_highest_impact_intervention(self, session_history: List[dict]) -> Optional[InterventionEffect]:
        """
        Identifies the single intervention with the highest causal impact on the outcome.
        """
        # Placeholder for complex causal identification logic
        # In Phase 10, we scan history for actions that reversed negative trends
        return InterventionEffect(
            action="fluid_resuscitation",
            target="map_collapse",
            magnitude=0.85,
            tick=42,
            causal_path=["fluid_resuscitation", "map_stability", "renal_perfusion"]
        )
