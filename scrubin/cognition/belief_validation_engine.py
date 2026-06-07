from __future__ import annotations

"""Deterministic belief‑validation engine – updates confidence and status of
existing beliefs based on the current set of supporting patterns.

The engine is observational only; it never influences other cognition modules.
"""

from dataclasses import replace
from typing import List

from scrubin.core.events import TimelineEvent
from scrubin.world.state import WorldState
from scrubin.cognition.learning_state import LearningState, Belief, LearningPattern


class BeliefValidationEngine:
    """Engine that validates and updates deterministic beliefs.

    For each belief, the engine recomputes confidence as the average confidence
    of all currently supporting patterns.  It then classifies the belief's
    ``validation_state`` according to deterministic thresholds:

    * confidence >= 0.8 → ``STABLE``
    * confidence >= 0.5 → ``WEAKENING``
    * otherwise        → ``CONTRADICTED``

    ``support_count`` is set to the number of supporting patterns, and
    ``last_validated_tick`` records when the validation occurred.
    """

    def __init__(self, rng):
        # ``rng`` retained for API compatibility – not used.
        self.rng = rng

    @staticmethod
    def _determine_state(confidence: float) -> str:
        if confidence >= 0.8:
            return "STABLE"
        if confidence >= 0.5:
            return "WEAKENING"
        return "CONTRADICTED"

    def evolve(self, world: WorldState) -> WorldState:
        learning_state: LearningState = getattr(world, "learning_state", LearningState())
        pattern_map = {p.pattern_id: p for p in learning_state.patterns}
        new_events: List[TimelineEvent] = []

        # Process beliefs in deterministic order.
        for belief in sorted(learning_state.beliefs, key=lambda b: b.belief_id):
            # Gather the currently existing supporting patterns.
            supporting = [pattern_map[pid] for pid in belief.supporting_pattern_ids if pid in pattern_map]
            if supporting:
                confidence = min(1.0, sum(p.confidence for p in supporting) / len(supporting))
            else:
                confidence = 0.0
            validation_state = self._determine_state(confidence)
            updated = replace(
                belief,
                confidence=confidence,
                validation_state=validation_state,
                support_count=len(supporting),
                contradiction_count=0,  # not tracked yet
                last_validated_tick=world.tick,
                updated_tick=world.tick,
            )
            learning_state = learning_state.replace_belief(updated)
            new_events.append(TimelineEvent(tick=world.tick, description=f"belief_validated:{belief.belief_id}"))

        world = world.with_learning_state(learning_state)
        # Batch append events.
        world = world.append_timeline(new_events) if new_events else world
        return world
