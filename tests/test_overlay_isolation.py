"""Overlay isolation validation test.

Confirms that distinct semantic overlays remain independent by ensuring that two
separate ``ActiveSemanticGraph`` instances do not share concept identifiers.
"""

from scrubin.ontology.active_graph import ActiveSemanticNode, ActiveSemanticGraph


def test_overlay_concept_isolation():
    # Overlay 1 – concept X.
    node_x = ActiveSemanticNode(concept_id="X", activation_score=0.4, activation_source="overlay1", activation_tick=0)
    graph1 = ActiveSemanticGraph(active_nodes=(node_x,))

    # Overlay 2 – concept Y.
    node_y = ActiveSemanticNode(concept_id="Y", activation_score=0.7, activation_source="overlay2", activation_tick=0)
    graph2 = ActiveSemanticGraph(active_nodes=(node_y,))

    ids1 = {n.concept_id for n in graph1.active_nodes}
    ids2 = {n.concept_id for n in graph2.active_nodes}
    # Ensure there is no overlap between the two overlays.
    assert ids1.isdisjoint(ids2)
