"""Append‑only deterministic store for knowledge‑graph nodes and edges.

Provides O(1) look‑ups by ID and deterministic query ordering. All updates
are performed via ``replace`` – no in‑place mutation.
"""

from __future__ import annotations

from dataclasses import replace
from typing import List, Tuple, Dict, Optional

from .knowledge_graph import GraphNode, GraphEdge, deterministic_edge_hash


class GraphStore:
    """Deterministic, append‑only store for a knowledge graph.

    * ``_nodes`` – list preserving insertion order.
    * ``_edges`` – list preserving insertion order.
    * Indexes for O(1) look‑ups.
    """

    def __init__(self) -> None:
        self._nodes: List[GraphNode] = []
        self._edges: List[GraphEdge] = []
        self._node_index: dict[str, int] = {}
        self._edge_index: dict[str, int] = {}
        self._outgoing: dict[str, List[int]] = {}
        self._incoming: dict[str, List[int]] = {}

    # ---------------------------------------------------------------------
    # Node API – deterministic append‑only semantics
    # ---------------------------------------------------------------------
    def add_node(self, node: GraphNode) -> None:
        """Add a node if it does not already exist.

        Nodes are identified by their deterministic ``id``. If a node with the same
        ``id`` already exists, the call is a no‑op (the original immutable node is
        retained).
        """
        if node.id in self._node_index:
            return
        self._nodes.append(node)
        self._node_index[node.id] = len(self._nodes) - 1
        self._outgoing.setdefault(node.id, [])
        self._incoming.setdefault(node.id, [])

    @property
    def nodes(self) -> Tuple[GraphNode, ...]:
        """Immutable view of all nodes in insertion order."""
        return tuple(self._nodes)

    # ---------------------------------------------------------------------
    # Edge API – deterministic merging of duplicate edges
    # ---------------------------------------------------------------------
    def add_edge(self, edge: GraphEdge) -> None:
        """Add an edge or merge with an existing one.

        Duplicate edges (same ``source``, ``predicate``, ``destination``) are merged
        deterministically: supporting belief/reflection lists are concatenated in
        insertion order, and confidence is recomputed as a weighted mean based on the
        total number of supporting items.
        """
        if edge.id in self._edge_index:
            # Merge with existing edge
            idx = self._edge_index[edge.id]
            prior = self._edges[idx]
            # If the new edge adds no new support, keep prior unchanged
            new_support = (
                set(edge.supporting_beliefs) | set(prior.supporting_beliefs),
                set(edge.supporting_reflections) | set(prior.supporting_reflections),
            )
            if (
                set(edge.supporting_beliefs).issubset(prior.supporting_beliefs)
                and set(edge.supporting_reflections).issubset(prior.supporting_reflections)
            ):
                return
            # Compute merged confidence weighted by support counts
            prior_count = len(prior.supporting_beliefs) + len(prior.supporting_reflections)
            new_count = len(edge.supporting_beliefs) + len(edge.supporting_reflections)
            merged_conf = (
                prior.confidence * prior_count + edge.confidence * new_count
            ) / (prior_count + new_count) if (prior_count + new_count) > 0 else 0.0
            merged = GraphEdge(
                id=prior.id,
                source=prior.source,
                predicate=prior.predicate,
                destination=prior.destination,
                confidence=merged_conf,
                supporting_beliefs=tuple(prior.supporting_beliefs + edge.supporting_beliefs),
                supporting_reflections=tuple(prior.supporting_reflections + edge.supporting_reflections),
                replay_hash="",
            )
            self._edges[idx] = replace(merged, replay_hash=deterministic_edge_hash(merged))
            return
        # New edge – add to store and indices
        self._edges.append(edge)
        self._edge_index[edge.id] = len(self._edges) - 1
        self._outgoing.setdefault(edge.source, []).append(self._edge_index[edge.id])
        self._incoming.setdefault(edge.destination, []).append(self._edge_index[edge.id])

    @property
    def edges(self) -> Tuple[GraphEdge, ...]:
        """Immutable view of all edges in insertion order."""
        return tuple(self._edges)

    # ---------------------------------------------------------------------
    # Query helpers
    # ---------------------------------------------------------------------
    def outgoing_edges(self, node_id: str) -> Tuple[GraphEdge, ...]:
        idxs = self._outgoing.get(node_id, [])
        return tuple(self._edges[i] for i in idxs)

    def incoming_edges(self, node_id: str) -> Tuple[GraphEdge, ...]:
        idxs = self._incoming.get(node_id, [])
        return tuple(self._edges[i] for i in idxs)

    # ---------------------------------------------------------------------
    # Statistics
    # ---------------------------------------------------------------------
    def node_count(self) -> int:
        return len(self._nodes)

    def edge_count(self) -> int:
        return len(self._edges)

    def summary(self) -> Tuple[int, int]:
        return (self.node_count(), self.edge_count())
