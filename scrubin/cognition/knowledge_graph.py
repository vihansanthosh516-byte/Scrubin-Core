"""Immutable graph structures for deterministic knowledge representation.

Nodes and edges are frozen dataclasses; updates are performed by creating new
instances via ``replace``. All identifiers and replay hashes are derived from
canonical JSON representations to guarantee replay safety.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from typing import Tuple


def deterministic_node_id(label: str, node_type: str) -> str:
    """Deterministic identifier for a graph node.

    The ID is ``node-`` + first 12 hex characters of the SHA‑256 hash of a
    canonical JSON representation of ``label`` and ``node_type``.
    """
    canonical = json.dumps({"label": label, "node_type": node_type}, separators=(",", ":"), sort_keys=True)
    return f"node-{hashlib.sha256(canonical.encode()).hexdigest()[:12]}"


def deterministic_node_hash(node: "GraphNode") -> str:
    """Deterministic replay hash for a fully populated ``GraphNode``."""
    data = {"id": node.id, "label": node.label, "node_type": node.node_type}
    json_repr = json.dumps(data, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(json_repr.encode()).hexdigest()


def deterministic_edge_id(source: str, predicate: str, destination: str) -> str:
    """Deterministic identifier for a graph edge.

    Uses SHA‑256 over ``source``, ``predicate`` and ``destination``.
    """
    canonical = json.dumps({"source": source, "predicate": predicate, "destination": destination}, separators=(",", ":"), sort_keys=True)
    return f"edge-{hashlib.sha256(canonical.encode()).hexdigest()[:12]}"


def deterministic_edge_hash(edge: "GraphEdge") -> str:
    """Deterministic replay hash for a fully populated ``GraphEdge``."""
    data = {
        "id": edge.id,
        "source": edge.source,
        "predicate": edge.predicate,
        "destination": edge.destination,
        "confidence": edge.confidence,
        "supporting_beliefs": list(edge.supporting_beliefs),
        "supporting_reflections": list(edge.supporting_reflections),
    }
    json_repr = json.dumps(data, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(json_repr.encode()).hexdigest()


@dataclass(frozen=True)
class GraphNode:
    """Immutable node in the deterministic knowledge graph."""
    id: str
    label: str
    node_type: str
    replay_hash: str

    @staticmethod
    def create(label: str, node_type: str) -> "GraphNode":
        node_id = deterministic_node_id(label, node_type)
        placeholder = GraphNode(id=node_id, label=label, node_type=node_type, replay_hash="")
        return replace(placeholder, replay_hash=deterministic_node_hash(placeholder))


@dataclass(frozen=True)
class GraphEdge:
    """Immutable directed edge in the deterministic knowledge graph."""
    id: str
    source: str
    predicate: str
    destination: str
    confidence: float
    supporting_beliefs: Tuple[str, ...]
    supporting_reflections: Tuple[str, ...]
    replay_hash: str

    @staticmethod
    def create(
        source: str,
        predicate: str,
        destination: str,
        confidence: float,
        supporting_beliefs: Tuple[str, ...] = (),
        supporting_reflections: Tuple[str, ...] = (),
    ) -> "GraphEdge":
        edge_id = deterministic_edge_id(source, predicate, destination)
        placeholder = GraphEdge(
            id=edge_id,
            source=source,
            predicate=predicate,
            destination=destination,
            confidence=confidence,
            supporting_beliefs=supporting_beliefs,
            supporting_reflections=supporting_reflections,
            replay_hash="",
        )
        return replace(placeholder, replay_hash=deterministic_edge_hash(placeholder))

# ---------------------------------------------------------------------------
# KnowledgeGraph – immutable container for KnowledgeNode/KnowledgeEdge
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class KnowledgeNode:
    """Immutable node in the knowledge graph used by KnowledgeGraphEngine."""
    node_id: str
    node_type: str
    description: str
    tick: int

@dataclass(frozen=True)
class KnowledgeEdge:
    """Immutable edge in the knowledge graph."""
    source_id: str
    target_id: str
    edge_type: str
    tick: int

@dataclass(frozen=True)
class KnowledgeGraph:
    """Immutable container for nodes and edges with deterministic append‑only semantics."""
    nodes: Tuple[KnowledgeNode, ...] = field(default_factory=tuple)
    edges: Tuple[KnowledgeEdge, ...] = field(default_factory=tuple)

    def add_node(self, node: KnowledgeNode) -> "KnowledgeGraph":
        if any(n.node_id == node.node_id for n in self.nodes):
            return self
        # Insert node and maintain sorted order by node_id for deterministic ordering
        new_nodes = self.nodes + (node,)
        sorted_nodes = tuple(sorted(new_nodes, key=lambda n: n.node_id))
        return replace(self, nodes=sorted_nodes)

    def add_edge(self, edge: KnowledgeEdge) -> "KnowledgeGraph":
        if any(e.source_id == edge.source_id and e.target_id == edge.target_id and e.edge_type == edge.edge_type for e in self.edges):
            return self
        # Insert edge and maintain sorted order for deterministic ordering
        new_edges = self.edges + (edge,)
        sorted_edges = tuple(sorted(new_edges, key=lambda e: (e.source_id, e.target_id, e.edge_type)))
        return replace(self, edges=sorted_edges)

