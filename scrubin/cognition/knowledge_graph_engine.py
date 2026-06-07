from __future__ import annotations

"""Deterministic knowledge‑graph engine – builds explicit relationships between
observations, patterns, and beliefs.

The engine is purely observational; it never influences planning, execution,
arbitration, or goal management. It only enriches the ``WorldState`` with a
``KnowledgeGraph`` that can be traversed for explanations.
"""

from dataclasses import replace
from typing import List

from scrubin.core.events import TimelineEvent
from scrubin.world.state import WorldState
from scrubin.cognition.learning_state import LearningState, LearningObservation, LearningPattern, Belief
from scrubin.cognition.knowledge_graph import KnowledgeGraph, KnowledgeNode, KnowledgeEdge


class KnowledgeGraphEngine:
    """Engine that constructs a deterministic knowledge graph.

    For each observation, pattern, and belief present in ``LearningState`` it
    creates a ``KnowledgeNode`` (if not already present) and adds ``SUPPORTS``
    edges:

    * Observation → Pattern (when the observation id appears in the pattern's
      ``source_observation_ids``)
    * Pattern → Belief (when the pattern id appears in the belief's
      ``supporting_pattern_ids``)
    """

    def __init__(self, rng):
        # ``rng`` retained for API compatibility – not used.
        self.rng = rng

    def evolve(self, world: WorldState) -> WorldState:
        learning_state: LearningState = getattr(world, "learning_state", LearningState())
        graph: KnowledgeGraph = getattr(world, "knowledge_graph", KnowledgeGraph())
        new_events: List[TimelineEvent] = []

        # Helper dictionaries for fast lookup.
        obs_map = {obs.id: obs for obs in learning_state.observations}
        pat_map = {pat.pattern_id: pat for pat in learning_state.patterns}
        belief_map = {bel.belief_id: bel for bel in learning_state.beliefs}

        # ---- Add nodes -------------------------------------------------------
        # Observations
        for obs in sorted(learning_state.observations, key=lambda o: o.id):
            node = KnowledgeNode(
                node_id=obs.id,
                node_type="OBSERVATION",
                description=obs.lesson,
                tick=obs.tick,
            )
            if not any(n.node_id == node.node_id for n in graph.nodes):
                graph = graph.add_node(node)
                new_events.append(TimelineEvent(tick=world.tick, description=f"knowledge_node_added:{node.node_id}"))

        # Patterns
        for pat in sorted(learning_state.patterns, key=lambda p: p.pattern_id):
            node = KnowledgeNode(
                node_id=pat.pattern_id,
                node_type="PATTERN",
                description=pat.description,
                tick=pat.first_tick,
            )
            if not any(n.node_id == node.node_id for n in graph.nodes):
                graph = graph.add_node(node)
                new_events.append(TimelineEvent(tick=world.tick, description=f"knowledge_node_added:{node.node_id}"))

        # Beliefs
        for bel in sorted(learning_state.beliefs, key=lambda b: b.belief_id):
            node = KnowledgeNode(
                node_id=bel.belief_id,
                node_type="BELIEF",
                description=bel.description,
                tick=bel.created_tick,
            )
            if not any(n.node_id == node.node_id for n in graph.nodes):
                graph = graph.add_node(node)
                new_events.append(TimelineEvent(tick=world.tick, description=f"knowledge_node_added:{node.node_id}"))

        # ---- Add edges -------------------------------------------------------
        # Observation -> Pattern (SUPPORTS)
        for pat in learning_state.patterns:
            for obs_id in pat.source_observation_ids:
                if obs_id not in obs_map:
                    continue  # observation may have been removed; skip.
                edge = KnowledgeEdge(
                    source_id=obs_id,
                    target_id=pat.pattern_id,
                    edge_type="SUPPORTS",
                    tick=world.tick,
                )
                if not any(e.source_id == edge.source_id and e.target_id == edge.target_id and e.edge_type == edge.edge_type for e in graph.edges):
                    graph = graph.add_edge(edge)
                    new_events.append(TimelineEvent(tick=world.tick, description=f"knowledge_edge_added:{edge.source_id}->{edge.target_id}:{edge.edge_type}"))

        # Pattern -> Belief (SUPPORTS)
        for bel in learning_state.beliefs:
            for pat_id in bel.supporting_pattern_ids:
                if pat_id not in pat_map:
                    continue
                edge = KnowledgeEdge(
                    source_id=pat_id,
                    target_id=bel.belief_id,
                    edge_type="SUPPORTS",
                    tick=world.tick,
                )
                if not any(e.source_id == edge.source_id and e.target_id == edge.target_id and e.edge_type == edge.edge_type for e in graph.edges):
                    graph = graph.add_edge(edge)
                    new_events.append(TimelineEvent(tick=world.tick, description=f"knowledge_edge_added:{edge.source_id}->{edge.target_id}:{edge.edge_type}"))

        # Apply updated graph and emit events.
        world = world.with_knowledge_graph(graph)
        # Batch append events.
        world = world.append_timeline(new_events) if new_events else world
        return world
