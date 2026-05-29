"""Deterministic semantic prediction engine.

Given the current ``WorldState`` (including ``active_semantic_graph`` and the
semantic intent graph) the engine forecasts likely future complications and
physiologic degradations.  It produces deterministic ``TimelineEvent`` objects
that downstream components (strategic planning, attention arbitration, etc.)
can consume.
"""

from __future__ import annotations

from typing import List, Tuple

from scrubin.world.state import WorldState, TimelineEvent
from scrubin.ontology.active_graph import ActiveSemanticGraph, ActiveSemanticNode
from scrubin.ontology.causal_engine import CausalEngine


class SemanticPredictionEngine:
    """Predict future semantic events based on current activation.

    * Traverses causal chains from highly activated nodes.
    * Scores each potential downstream concept by a deterministic risk metric.
    * Emits ``semantic_risk_escalating`` and ``predicted_<concept>`` events.
    """

    def __init__(self, rng) -> None:
        self.rng = rng  # retained for future deterministic tie‑breaks
        self.causal_engine = CausalEngine()

    def predict(self, world: WorldState) -> WorldState:
        graph: ActiveSemanticGraph = world.active_semantic_graph
        events: List[TimelineEvent] = []
        for node in graph.active_nodes:
            # Only consider nodes with a non‑trivial activation score.
            if node.activation_score < 0.2:
                continue
            # Retrieve deterministic causal chains up to depth 3.
            chain = self.causal_engine.trace_causal_chain(node.concept_id, depth=3)
            for src, rel, tgt in chain:
                # Assign a deterministic risk score – activation * salience.
                risk = node.activation_score * node.causal_salience * 0.5
                if risk > 0.15:
                    # Emit a prediction event for the target concept.
                    events.append(
                        TimelineEvent(
                            world.tick,
                            f"predicted_{tgt}:from_{src}",
                        )
                    )
        # If any risk events were generated, also emit a generic escalation flag.
        if events:
            events.append(TimelineEvent(world.tick, "semantic_risk_escalating"))
        new_world = world
        for ev in events:
            new_world = new_world.append_timeline(ev)
        return new_world
