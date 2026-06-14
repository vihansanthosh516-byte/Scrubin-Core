"""Deterministic knowledge‑graph construction from beliefs and reflections.

The builder consumes ``BeliefStore`` and ``ReflectionStore`` and populates a
``GraphStore`` with nodes and edges. No AI or randomness is involved – the
mapping from belief/reflection statements to graph triples is deterministic.
"""

from __future__ import annotations

from typing import Tuple

from .belief_store import BeliefStore
from .reflection_store import ReflectionStore
from .graph_store import GraphStore
from .knowledge_graph import GraphNode, GraphEdge


def _split_statement(statement: str) -> Tuple[str, str, str]:
    """Deterministically split a statement into ``subject``, ``predicate`` and ``object``.

    The function expects a statement of the form ``"subject predicate object"``.
    If the statement contains fewer than three tokens, the missing parts are
    returned as empty strings. This deterministic parsing ensures identical
    graph construction across replays.
    """
    parts = statement.split()
    if len(parts) >= 3:
        subject = parts[0]
        predicate = parts[1]
        obj = " ".join(parts[2:])
    elif len(parts) == 2:
        subject, predicate = parts
        obj = ""
    elif len(parts) == 1:
        subject = parts[0]
        predicate = obj = ""
    else:
        subject = predicate = obj = ""
    return subject, predicate, obj


def update_graph(belief_store: BeliefStore, reflection_store: ReflectionStore, graph_store: GraphStore) -> None:
    """Populate ``graph_store`` from ``belief_store`` and ``reflection_store``.

    * For each belief, create a node for the subject and object (both of type
      ``"belief_entity"``) and a deterministic edge ``subject ──predicate──▶ object``.
    * For each reflection, create a node for the subject (the first token of the
      statement) and a node for the object (the rest of the statement) with type
      ``"reflection_entity"``. The edge predicate is the second token of the
      statement (if present) else ``"relates"``.
    * Edge confidence is the mean of the supporting belief confidences (for
      belief‑derived edges) or the reflection confidence (for reflection‑derived
      edges).
    * Duplicate edges are merged deterministically by ``GraphStore.add_edge``.
    """
    # Process beliefs
    for belief in belief_store.beliefs:
        subject, predicate, obj = _split_statement(belief.statement)
        if not subject or not predicate or not obj:
            continue
        # Create nodes (type ``belief_entity``)
        subj_node = GraphNode.create(label=subject, node_type="belief_entity")
        obj_node = GraphNode.create(label=obj, node_type="belief_entity")
        graph_store.add_node(subj_node)
        graph_store.add_node(obj_node)
        # Edge
        edge = GraphEdge.create(
            source=subj_node.id,
            predicate=predicate,
            destination=obj_node.id,
            confidence=belief.confidence,
            supporting_beliefs=(belief.id,),
            supporting_reflections=(),
        )
        graph_store.add_edge(edge)

    # Process reflections
    for refl in reflection_store.reflections:
        subject, predicate, obj = _split_statement(refl.statement)
        if not subject:
            continue
        # Use a default predicate if missing
        pred = predicate if predicate else "relates"
        # Destination is the remainder of the statement after subject and predicate
        destination = obj if obj else ""
        # Create nodes (type ``reflection_entity``)
        subj_node = GraphNode.create(label=subject, node_type="reflection_entity")
        dest_label = destination if destination else subject  # fallback to subject when no object
        dest_node = GraphNode.create(label=dest_label, node_type="reflection_entity")
        graph_store.add_node(subj_node)
        graph_store.add_node(dest_node)
        # Edge confidence derived from reflection confidence
        edge = GraphEdge.create(
            source=subj_node.id,
            predicate=pred,
            destination=dest_node.id,
            confidence=refl.confidence,
            supporting_beliefs=(),
            supporting_reflections=(refl.id,),
        )
        graph_store.add_edge(edge)
