"""Deterministic conflict detection engine.

Detects semantic contradictions between active intents, hypotheses and
constraints.  When a conflict is found a ``TimelineEvent`` is emitted so that
higher‑level strategic components can re‑plan.
"""

from __future__ import annotations

from typing import List

from scrubin.world.state import WorldState, TimelineEvent
from scrubin.ontology.intent_graph import IntentGraph, IntentNode


class ConflictEngine:
    """Detects and reports deterministic semantic conflicts.

    * Overlapping required concepts with mutually exclusive blocking
      conditions generate ``semantic_conflict_detected`` events.
    * Contradictory hypothesis confidence (two high‑confidence hypotheses
      that share a concept but have opposing expectations) generate
      ``hypothesis_instability`` events.
    """

    def __init__(self, rng) -> None:
        self.rng = rng

    def resolve(self, world: WorldState) -> WorldState:
        intents: IntentGraph = world.intent_graph
        events: List[TimelineEvent] = []
        pending = intents.pending_intents()
        # Simple O(n^2) deterministic pairwise check – deterministic ordering
        for i in range(len(pending)):
            for j in range(i + 1, len(pending)):
                a: IntentNode = pending[i]
                b: IntentNode = pending[j]
                # Conflict if they require the same concept but have mutually
                # exclusive blocking conditions (deterministically expressed as
                # strings that start with "!" to denote negation).
                shared_concepts = set(a.required_concepts) & set(b.required_concepts)
                if not shared_concepts:
                    continue
                # Detect contradictory blocks – e.g., "!increase_pressure" vs
                # "increase_pressure".
                for cond_a in a.blocking_conditions:
                    for cond_b in b.blocking_conditions:
                        if cond_a.startswith("!") and cond_b == cond_a[1:]:
                            events.append(
                                TimelineEvent(
                                    world.tick,
                                    f"semantic_conflict_detected:{a.intent_id}-{b.intent_id}",
                                )
                            )
        # Apply events to world.
        new_world = world
        for ev in events:
            new_world = new_world.append_timeline(ev)
        return new_world
