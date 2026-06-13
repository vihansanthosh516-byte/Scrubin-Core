from __future__ import annotations

"""Deterministic knowledge graph – stores explicit relationships between
observations, patterns, and beliefs for traceability and explanation.

All objects are immutable and updated via functional ``replace`` calls to keep
the system replay‑safe.
"""

from dataclasses import dataclass, field, replace
from typing import Tuple


@dataclass(frozen=True)
class KnowledgeNode:
    """Immutable node in the knowledge graph.

    * ``node_id`` – deterministic identifier (e.g. observation id, pattern id,
      belief id).
    * ``node_type`` – one of ``OBSERVATION``, ``PATTERN``, ``BELIEF``.
    * ``description`` – human readable text.
    * ``tick`` – world tick at which the node was created/observed.
    """

    node_id: str
    node_type: str
    description: str
    tick: int


@dataclass(frozen=True)
class KnowledgeEdge:
    """Immutable directed edge in the knowledge graph.

    * ``source_id`` – ``node_id`` of the source node.
    * ``target_id`` – ``node_id`` of the target node.
    * ``edge_type`` – relationship label (e.g. ``SUPPORTS``).
    * ``tick`` – world tick when the edge was added.
    """

    source_id: str
    target_id: str
    edge_type: str
    tick: int


@dataclass(frozen=True)
class KnowledgeGraph:
    """Container for deterministic knowledge graph nodes and edges.

    The collections are tuples to guarantee deterministic ordering.
    """

    nodes: Tuple[KnowledgeNode, ...] = field(default_factory=tuple)
    edges: Tuple[KnowledgeEdge, ...] = field(default_factory=tuple)

    def add_node(self, node: KnowledgeNode) -> "KnowledgeGraph":
        """Add a node if its ``node_id`` does not already exist.

        Returns a new ``KnowledgeGraph`` with the node inserted in sorted order.
        """
        # Fast‑path: if there are no nodes, we can add the new node without a linear scan.
        if not self.nodes:
            return replace(self, nodes=(node,))
        if any(n.node_id == node.node_id for n in self.nodes):
            return self
        new_nodes = tuple(sorted(self.nodes + (node,), key=lambda n: n.node_id))
        return replace(self, nodes=new_nodes)

    def add_edge(self, edge: KnowledgeEdge) -> "KnowledgeGraph":
        """Add an edge if the exact ``source_id``/``target_id``/``edge_type`` pair
        is not already present.
        """
        # Fast‑path: if there are no edges, add directly.
        if not self.edges:
            return replace(self, edges=(edge,))
        if any(e.source_id == edge.source_id and e.target_id == edge.target_id and e.edge_type == edge.edge_type for e in self.edges):
            return self
        new_edges = tuple(sorted(self.edges + (edge,), key=lambda e: (e.source_id, e.target_id, e.edge_type)))
        return replace(self, edges=new_edges)
