from __future__ import annotations

"""Deterministic pattern extraction engine – converts learning observations
into high‑level learning patterns without influencing any other cognition
components.

The engine is pure and replay‑safe: it only reads ``LearningState``
observations, produces ``LearningPattern`` entries, updates the ``LearningState``
and emits timeline events.
"""

from dataclasses import replace
from typing import List, Tuple, Dict

from scrubin.core.events import TimelineEvent
from scrubin.world.state import WorldState
from scrubin.cognition.learning_state import LearningState, LearningObservation, LearningPattern


class PatternExtractionEngine:
    """Engine that extracts deterministic patterns from observations.

    The ``evolve`` method is called after the ``MetaLearningEngine``.
    It groups observations by their ``lesson`` (and optionally category & tags)
    and creates a ``LearningPattern`` for each unique group that does not yet
    have a pattern.
    """

    def __init__(self, rng):
        # ``rng`` retained for API compatibility – not used.
        self.rng = rng

    @staticmethod
    def _sanitize_key(text: str) -> str:
        """Return a deterministic identifier derived from *text*.

        Non‑alphanumeric characters are replaced with underscores and the result is
        lower‑cased.  This yields a stable ``pattern_id`` without any random
        components.
        """
        # Simple deterministic sanitisation.
        sanitized = "".join(c if c.isalnum() else "_" for c in text)
        # Collapse multiple underscores and strip leading/trailing ones.
        sanitized = "_".join(filter(None, sanitized.split("_")))
        return sanitized.lower()

    def evolve(self, world: WorldState) -> WorldState:
        # Retrieve current LearningState (fallback to defaults).
        learning_state: LearningState = getattr(world, "learning_state", LearningState())
        observations: Tuple[LearningObservation, ...] = learning_state.observations
        existing_pattern_ids = {p.pattern_id for p in learning_state.patterns}
        new_events: List[TimelineEvent] = []

        # Group observations by a deterministic key (category, lesson, tags).
        groups: Dict[Tuple[str, str, Tuple[str, ...]], List[LearningObservation]] = {}
        for obs in observations:
            key = (obs.category, obs.lesson, obs.tags)
            groups.setdefault(key, []).append(obs)

        # Process groups in deterministic order (sorted by the key tuple).
        for key in sorted(groups.keys()):
            obs_list = groups[key]
            category, lesson, tags = key
            # Derive a deterministic pattern identifier from the lesson text.
            sanitized = self._sanitize_key(lesson)
            pattern_id = f"pattern_{sanitized}" if sanitized else f"pattern_{category}"
            if pattern_id in existing_pattern_ids:
                continue  # Pattern already exists – skip.

            occurrences = len(obs_list)
            first_tick = min(o.tick for o in obs_list)
            last_tick = max(o.tick for o in obs_list)
            # Deterministic confidence: occurrences divided by (world.tick - first_tick + 1)
            # Clamp to [0.0, 1.0].
            denominator = max(1, world.tick - first_tick + 1)
            confidence = min(1.0, occurrences / denominator)
            pattern = LearningPattern(
                pattern_id=pattern_id,
                pattern_type="REPETITIVE",
                description=lesson,
                occurrences=occurrences,
                confidence=confidence,
                first_tick=first_tick,
                last_tick=last_tick,
                source_observation_ids=tuple(sorted(o.id for o in obs_list)),
            )
            learning_state = learning_state.add_pattern(pattern)
            new_events.append(TimelineEvent(tick=world.tick, description=f"learning_pattern_created:{pattern_id}"))

        # Update world with new learning state and emit events.
        world = world.with_learning_state(learning_state)
        # Batch append events.
        world = world.append_timeline(new_events) if new_events else world
        return world
