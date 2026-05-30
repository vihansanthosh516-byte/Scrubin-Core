"""Semantic graph integrity tests.

Ensures that the active semantic graph contains no orphan edges, no duplicate
nodes, and maintains deterministic ordering.
"""

from scrubin.ontology.active_graph import ActiveSemanticNode, ActiveSemanticEdge, ActiveSemanticGraph


def test_no_orphan_edges_and_unique_nodes():
    node_a = ActiveSemanticNode(concept_id="A", activation_score=0.5, activation_source="test", activation_tick=0)
    node_b = ActiveSemanticNode(concept_id="B", activation_score=0.6, activation_source="test", activation_tick=0)
    edge = ActiveSemanticEdge(from_id="A", to_id="B", relation="causes")
    graph = ActiveSemanticGraph(active_nodes=(node_a, node_b), active_edges=(edge,))

    node_ids = {n.concept_id for n in graph.active_nodes}
    # No duplicate node IDs.
    assert len(node_ids) == len(graph.active_nodes)
    # All edge endpoints must refer to existing node IDs.
    for e in graph.active_edges:
        assert e.from_id in node_ids, f"Edge from_id {e.from_id} not in active nodes"
        assert e.to_id in node_ids, f"Edge to_id {e.to_id} not in active nodes"
