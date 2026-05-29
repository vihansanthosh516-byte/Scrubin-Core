"""Deterministic semantic activation engine.

The engine operates on ``ActiveSemanticGraph`` stored inside ``WorldState``.
It provides deterministic activation, propagation, decay, pruning and focus
recalculation.  All operations are pure – a new ``WorldState`` is returned.
"""

from __future__ import annotations

from typing import List, Tuple

from scrubin.world.state import WorldState, TimelineEvent
from scrubin.ontology.active_graph import (
    ActiveSemanticGraph,
    ActiveSemanticNode,
    ActiveSemanticEdge,
)


class SemanticActivationEngine:
    """Deterministic engine that updates the active semantic graph each tick.

    * ``activate_concept`` – deterministic activation of a concept from a given
      source.
    * ``propagate`` – spreads activation along outgoing edges with deterministic
      weighting.
    * ``decay_and_prune`` – decays activation scores and removes stale nodes.
    * ``recalculate_focus`` – selects top‑priority concepts for ``semantic_focus``.
    """

    def __init__(self, rng) -> None:
        self.rng = rng  # retained for future extensions (e.g., deterministic tie‑breaks)

    # ---------------------------------------------------------------------
    # Public entry point – integrates all steps.
    # ---------------------------------------------------------------------
    def evolve(self, world: WorldState) -> WorldState:
        graph = world.active_semantic_graph
        # 1️⃣ Activation already performed by other engines (e.g., strategic,
        #    physiological) – this step only handles propagation, decay and focus.
        graph = self._propagate(graph)
        graph = self._decay_and_prune(graph)
        graph = self._recalculate_focus(graph)
        # Record tick advancement for the graph itself.
        graph = graph.with_graph_tick(graph.graph_tick + 1)
        # Emit timeline events for any focus shift.
        events: List[TimelineEvent] = []
        if graph.semantic_focus:
            events.append(TimelineEvent(world.tick, "semantic_focus_shift"))
        new_world = world.with_active_semantic_graph(graph)
        for ev in events:
            new_world = new_world.append_timeline(ev)
        return new_world

    # ---------------------------------------------------------------------
    # Deterministic activation – can be called by other engines.
    # ---------------------------------------------------------------------
    def activate_concept(
        self,
        world: WorldState,
        concept_id: str,
        source: str,
        score_increment: float = 0.1,
    ) -> WorldState:
        """Activate or strengthen a concept deterministically.

        If the concept is already present, its ``activation_score`` is increased
        by ``score_increment`` (clamped to 1.0).  If absent, a new node is added
        with the given ``source`` and an initial ``activation_score`` of
        ``score_increment``.
        """
        graph = world.active_semantic_graph
        node = graph.get_node(concept_id)
        if node is None:
            node = ActiveSemanticNode(
                concept_id=concept_id,
                activation_score=min(1.0, max(0.0, score_increment)),
                activation_source=source,
                activation_tick=world.tick,
                last_access_tick=world.tick,
                priority=0,
            )
        else:
            node = node.with_activation_score(node.activation_score + score_increment)
            node = node.with_last_access_tick(world.tick)
        graph = graph.replace_node(node)
        # Record activation history deterministically.
        history = graph.activation_history + ((world.tick, concept_id),)
        graph = graph.with_activation_history(history)
        return world.with_active_semantic_graph(graph)

    # ---------------------------------------------------------------------
    # Propagation – deterministic spreading of activation along edges.
    # ---------------------------------------------------------------------
    def _propagate(self, graph: ActiveSemanticGraph) -> ActiveSemanticGraph:
        # Simple deterministic rule: for each active node, propagate a fraction
        # of its activation_score to all outgoing edges proportional to edge.weight.
        updated_nodes: List[ActiveSemanticNode] = list(graph.active_nodes)
        node_map = {n.concept_id: n for n in updated_nodes}
        for node in graph.active_nodes:
            if node.activation_score <= 0.0:
                continue
            outgoing = [e for e in graph.active_edges if e.from_id == node.concept_id]
            for edge in outgoing:
                target = node_map.get(edge.to_id)
                if target is None:
                    # If target not yet active, create a lightweight node.
                    target = ActiveSemanticNode(
                        concept_id=edge.to_id,
                        activation_score=0.0,
                    )
                    updated_nodes.append(target)
                    node_map[edge.to_id] = target
                # Deterministic propagation amount.
                propagated = node.activation_score * edge.weight * 0.05
                new_score = min(1.0, target.activation_score + propagated)
                target = target.with_activation_score(new_score)
                node_map[edge.to_id] = target
        # Rebuild node tuple preserving deterministic order (sorted by concept_id).
        new_nodes = tuple(sorted(node_map.values(), key=lambda n: n.concept_id))
        return graph.with_active_nodes(new_nodes)

    # ---------------------------------------------------------------------
    # Decay & pruning – deterministic reduction of stale activations.
    # ---------------------------------------------------------------------
    def _decay_and_prune(self, graph: ActiveSemanticGraph) -> ActiveSemanticGraph:
        pruned_nodes: List[ActiveSemanticNode] = []
        for node in graph.active_nodes:
            decayed = max(0.0, node.activation_score - node.decay_rate)
            node = node.with_activation_score(decayed)
            # Deterministic pruning thresholds.
            if decayed >= 0.001:
                pruned_nodes.append(node)
        # Edges are kept only if both endpoints survive.
        remaining_ids = {n.concept_id for n in pruned_nodes}
        pruned_edges = tuple(
            e for e in graph.active_edges if e.from_id in remaining_ids and e.to_id in remaining_ids
        )
        # Sort nodes deterministically.
        pruned_nodes_sorted = tuple(sorted(pruned_nodes, key=lambda n: n.concept_id))
        return graph.with_active_nodes(pruned_nodes_sorted).with_active_edges(pruned_edges)

    # ---------------------------------------------------------------------
    # Focus recalculation – selects top‑priority concepts.
    # ---------------------------------------------------------------------
    def _recalculate_focus(self, graph: ActiveSemanticGraph) -> ActiveSemanticGraph:
        # Determine priority by activation_score * contextual_weight (deterministic).
        scored = [
            (n.activation_score * (1.0 + n.contextual_weight), n.concept_id) for n in graph.active_nodes
        ]
        # Sort descending by score, then ascending by concept_id for deterministic tie‑break.
        scored.sort(key=lambda x: (-x[0], x[1]))
        top_ids = tuple(cid for _, cid in scored[:3])  # top‑3 focus concepts
        return graph.with_semantic_focus(top_ids)
