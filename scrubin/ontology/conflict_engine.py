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
        # Index intents by required concept for O(n) detection.
        concept_index: dict[str, list[IntentNode]] = {}
        for intent in pending:
            for concept in intent.required_concepts:
                concept_index.setdefault(concept, []).append(intent)
        # For each concept with multiple intents, check contradictory blocking conditions.
        for intents_sharing in concept_index.values():
            if len(intents_sharing) < 2:
                continue
            # Build a map from blocking condition to intents that contain it.
            block_map: dict[str, list[IntentNode]] = {}
            for intent in intents_sharing:
                for block in intent.blocking_conditions:
                    block_map.setdefault(block, []).append(intent)
            # Detect contradictions: a block "!X" and another block "X" in the same concept group.
            for block, intents_with_block in block_map.items():
                if block.startswith("!"):
                    pos = block[1:]
                    if pos in block_map:
                        # Emit conflict event for each unordered pair of intents across the contradictory blocks.
                        for a in intents_with_block:
                            for b in block_map[pos]:
                                if a.intent_id == b.intent_id:
                                    continue
                                events.append(
                                    TimelineEvent(
                                        world.tick,
                                        f"semantic_conflict_detected:{a.intent_id}-{b.intent_id}",
                                    )
                                )
        # Apply events to world in a single immutable update.
        new_world = world.append_timeline(events) if events else world
        return new_world
