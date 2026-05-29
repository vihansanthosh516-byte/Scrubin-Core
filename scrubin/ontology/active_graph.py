"""Active semantic graph runtime structures.

These dataclasses represent the *working memory* of the ontology during a
simulation.  All objects are immutable – the engine creates new instances via
``replace`` so that the overall simulation remains deterministic and replay‑
safe.
"""

from __future__ import annotations

from dataclasses import dataclass, replace, field
from typing import Tuple


# ---------------------------------------------------------------------------
# Nodes and edges – immutable representations of an activated concept.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ActiveSemanticNode:
    """A single activated ontology concept.

    * ``concept_id`` – the unique identifier from the core ontology.
    * ``activation_score`` – current strength of activation (0.0‑1.0).
    * ``semantic_relevance`` – relevance to the current procedural context.
    * ``contextual_weight`` – weight derived from physiology / cognition.
    * ``activation_source`` – deterministic source that triggered the activation
      (e.g. ``"procedure_phase"``, ``"physiology"``).
    * ``activation_tick`` – simulation tick at which the activation occurred.
    * ``decay_rate`` – deterministic per‑tick decay applied to ``activation_score``.
    * ``causal_salience`` – importance of the node within a causal chain.
    * ``stability`` – 1.0 means fully stable, lower values indicate fragile
      activation (e.g., due to contradictory evidence).
    * ``priority`` – integer priority used for focus selection.
    * ``last_access_tick`` – last tick the node was accessed (used for LRU‑
      style pruning).
    """

    concept_id: str
    activation_score: float = 0.0
    semantic_relevance: float = 0.0
    contextual_weight: float = 0.0
    activation_source: str = ""
    activation_tick: int = 0
    decay_rate: float = 0.01
    causal_salience: float = 0.0
    stability: float = 1.0
    priority: int = 0
    last_access_tick: int = 0

    # ---------------------------------------------------------------------
    # Helper ``with_*`` methods – each returns a new immutable node.
    # ---------------------------------------------------------------------
    def with_activation_score(self, score: float) -> "ActiveSemanticNode":
        return replace(self, activation_score=min(1.0, max(0.0, score)))

    def with_semantic_relevance(self, relevance: float) -> "ActiveSemanticNode":
        return replace(self, semantic_relevance=min(1.0, max(0.0, relevance)))

    def with_contextual_weight(self, weight: float) -> "ActiveSemanticNode":
        return replace(self, contextual_weight=min(1.0, max(0.0, weight)))

    def with_activation_source(self, source: str) -> "ActiveSemanticNode":
        return replace(self, activation_source=source)

    def with_activation_tick(self, tick: int) -> "ActiveSemanticNode":
        return replace(self, activation_tick=tick)

    def with_decay_rate(self, decay: float) -> "ActiveSemanticNode":
        return replace(self, decay_rate=max(0.0, decay))

    def with_causal_salience(self, salience: float) -> "ActiveSemanticNode":
        return replace(self, causal_salience=salience)

    def with_stability(self, stability: float) -> "ActiveSemanticNode":
        return replace(self, stability=min(1.0, max(0.0, stability)))

    def with_priority(self, priority: int) -> "ActiveSemanticNode":
        return replace(self, priority=priority)

    def with_last_access_tick(self, tick: int) -> "ActiveSemanticNode":
        return replace(self, last_access_tick=tick)


@dataclass(frozen=True)
class ActiveSemanticEdge:
    """Directed edge between two active semantic nodes.

    ``relation`` holds a textual label (e.g. ``"causes"`` or ``"supplies"``).
    ``weight`` is a deterministic multiplier used during propagation.
    """

    from_id: str
    to_id: str
    relation: str = ""
    weight: float = 1.0

    def with_weight(self, weight: float) -> "ActiveSemanticEdge":
        return replace(self, weight=weight)

    def with_relation(self, relation: str) -> "ActiveSemanticEdge":
        return replace(self, relation=relation)


# ---------------------------------------------------------------------------
# Graph container – immutable collection of active nodes and edges.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ActiveSemanticGraph:
    """Runtime representation of the *activated* portion of the ontology.

    * ``active_nodes`` – tuple of ``ActiveSemanticNode`` objects.
    * ``active_edges`` – tuple of ``ActiveSemanticEdge`` objects.
    * ``semantic_focus`` – ordered tuple of concept ids that currently have the
      highest priority (used by option generation, explainability, etc.).
    * ``activation_history`` – deterministic record of (tick, concept_id) pairs.
    * ``active_domains`` – set of high‑level domain tags that currently contain
      active concepts (e.g. ``"anatomy"``, ``"pathology"``).
    * ``graph_tick`` – the current simulation tick for this graph.
    """

    active_nodes: Tuple[ActiveSemanticNode, ...] = field(default_factory=tuple)
    active_edges: Tuple[ActiveSemanticEdge, ...] = field(default_factory=tuple)
    semantic_focus: Tuple[str, ...] = field(default_factory=tuple)
    activation_history: Tuple[Tuple[int, str], ...] = field(default_factory=tuple)
    active_domains: Tuple[str, ...] = field(default_factory=tuple)
    graph_tick: int = 0

    # ---------------------------------------------------------------------
    # Helper methods – return new immutable graph instances.
    # ---------------------------------------------------------------------
    def with_active_nodes(self, nodes: Tuple[ActiveSemanticNode, ...]) -> "ActiveSemanticGraph":
        return replace(self, active_nodes=nodes)

    def with_active_edges(self, edges: Tuple[ActiveSemanticEdge, ...]) -> "ActiveSemanticGraph":
        return replace(self, active_edges=edges)

    def with_semantic_focus(self, focus: Tuple[str, ...]) -> "ActiveSemanticGraph":
        return replace(self, semantic_focus=focus)

    def with_activation_history(self, history: Tuple[Tuple[int, str], ...]) -> "ActiveSemanticGraph":
        return replace(self, activation_history=history)

    def with_active_domains(self, domains: Tuple[str, ...]) -> "ActiveSemanticGraph":
        return replace(self, active_domains=domains)

    def with_graph_tick(self, tick: int) -> "ActiveSemanticGraph":
        return replace(self, graph_tick=tick)

    # ---------------------------------------------------------------------
    # Convenience look‑ups.
    # ---------------------------------------------------------------------
    def get_node(self, concept_id: str) -> ActiveSemanticNode | None:
        for n in self.active_nodes:
            if n.concept_id == concept_id:
                return n
        return None

    def replace_node(self, node: ActiveSemanticNode) -> "ActiveSemanticGraph":
        # Remove any existing node with the same id and insert the new one at the end
        filtered = tuple(n for n in self.active_nodes if n.concept_id != node.concept_id)
        return self.with_active_nodes(filtered + (node,))

    def add_edge(self, edge: ActiveSemanticEdge) -> "ActiveSemanticGraph":
        # Avoid duplicate edges (deterministic ordering by tuple value)
        if edge in self.active_edges:
            return self
        return self.with_active_edges(self.active_edges + (edge,))
