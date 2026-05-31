from __future__ import annotations

"""Deterministic belief formation engine – converts learning patterns into high‑level beliefs.

The engine is purely observational: it reads ``LearningState.patterns`` and creates
``LearningState.beliefs`` without influencing any other cognition components.
"""

from dataclasses import replace
from typing import List

from scrubin.core.events import TimelineEvent
from scrubin.world.state import WorldState
from scrubin.cognition.learning_state import LearningState, LearningPattern, Belief


class BeliefFormationEngine:
    """Engine that forms deterministic beliefs from stable patterns.

    The ``evolve`` method is invoked after the ``PatternExtractionEngine``.
    For each pattern that does not already have a corresponding belief, a
    belief is generated.  The belief inherits the pattern's confidence and uses a
    deterministic identifier derived from the pattern identifier.
    """

    def __init__(self, rng):
        # ``rng`` retained for API compatibility – not used.
        self.rng = rng

    def evolve(self, world: WorldState) -> WorldState:
        learning_state: LearningState = getattr(world, "learning_state", LearningState())
        patterns: tuple[LearningPattern, ...] = learning_state.patterns
        existing_belief_ids = {b.belief_id for b in learning_state.beliefs}
        new_events: List[TimelineEvent] = []

        # Process patterns in deterministic order.
        # Build a dict for quick pattern lookup by id.
        pattern_dict = {p.pattern_id: p for p in patterns}
        for pattern in sorted(patterns, key=lambda p: p.pattern_id):
            # Deterministic belief identifier derived from the description.
            belief_id = f"belief_{self._sanitize_key(pattern.description)}"
            existing = next((b for b in learning_state.beliefs if b.belief_id == belief_id), None)
            if existing is None:
                # Create a new belief.
                belief_type = f"{pattern.pattern_type}_BELIEF"
                belief = Belief(
                    belief_id=belief_id,
                    belief_type=belief_type,
                    description=pattern.description,
                    confidence=pattern.confidence,
                    created_tick=world.tick,
                    updated_tick=world.tick,
                    supporting_pattern_ids=(pattern.pattern_id,),
                    validation_state="STABLE",
                    support_count=1,
                    contradiction_count=0,
                    last_validated_tick=world.tick,
                )
                learning_state = learning_state.add_belief(belief)
                new_events.append(TimelineEvent(tick=world.tick, description=f"belief_created:{belief_id}"))
            else:
                # Merge pattern into existing belief.
                # Union of supporting pattern ids.
                new_support = tuple(sorted(set(existing.supporting_pattern_ids + (pattern.pattern_id,))))
                # Re‑compute confidence from all supporting patterns.
                supporting_patterns = [pattern_dict[pid] for pid in new_support if pid in pattern_dict]
                if supporting_patterns:
                    confidence = min(1.0, sum(p.confidence for p in supporting_patterns) / len(supporting_patterns))
                else:
                    confidence = existing.confidence
                updated_belief = replace(
                    existing,
                    supporting_pattern_ids=new_support,
                    confidence=confidence,
                    updated_tick=world.tick,
                    support_count=len(new_support),
                    last_validated_tick=world.tick,
                )
                learning_state = learning_state.replace_belief(updated_belief)
                new_events.append(TimelineEvent(tick=world.tick, description=f"belief_updated:{belief_id}"))

        # Apply updated learning state and emit events.
        world = world.with_learning_state(learning_state)
        for ev in new_events:
            world = world.append_timeline(ev)
        return world

    @staticmethod
    def _sanitize_key(text: str) -> str:
        """Return a deterministic identifier derived from *text*.

        Non‑alphanumeric characters are replaced with underscores and the result
        is lower‑cased.
        """
        sanitized = "".join(c if c.isalnum() else "_" for c in text)
        sanitized = "_".join(filter(None, sanitized.split("_")))
        return sanitized.lower()
