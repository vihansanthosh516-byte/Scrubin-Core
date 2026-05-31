from __future__ import annotations

"""Deterministic learning memory state.

Provides immutable containers for observations collected from reflections.
All collections are tuples to guarantee deterministic ordering.
"""

from dataclasses import dataclass, field, replace
from typing import Tuple


@dataclass(frozen=True)
class LearningObservation:
    """Immutable record of a single learning observation.

    * ``id`` – unique identifier for the observation.
    * ``tick`` – world tick at which the observation was created.
    * ``source_reflection_id`` – identifier of the originating ``DecisionReflection``.
    * ``category`` – classification of the observation (e.g. outcome).
    * ``lesson`` – textual description of the lesson learned.
    * ``confidence`` – confidence score (0.0‑1.0).
    * ``severity`` – severity score (0.0‑1.0).
    * ``tags`` – deterministic sorted tuple of tags.
    """

    id: str
    tick: int
    source_reflection_id: str
    category: str
    lesson: str
    confidence: float
    severity: float
    tags: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self):
        # Ensure tags are stored in a deterministic sorted order.
        sorted_tags = tuple(sorted(self.tags))
        object.__setattr__(self, "tags", sorted_tags)


@dataclass(frozen=True)
class LearningPattern:
    """Immutable record of a deterministic learning pattern.

    * ``pattern_id`` – unique deterministic identifier for the pattern.
    * ``pattern_type`` – classification of the pattern (e.g. RECURRING, ANOMALY).
    * ``description`` – human‑readable description of the pattern.
    * ``occurrences`` – number of observations that match the pattern.
    * ``confidence`` – deterministic confidence derived from occurrence count and tick history.
    * ``first_tick`` – tick of the earliest matching observation.
    * ``last_tick`` – tick of the latest matching observation.
    * ``source_observation_ids`` – tuple of observation IDs that contributed to the pattern.
    """

    pattern_id: str
    pattern_type: str
    description: str
    occurrences: int
    confidence: float
    first_tick: int
    last_tick: int
    source_observation_ids: Tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Belief:
    """Immutable record of a deterministic belief derived from patterns.

    * ``belief_id`` – unique deterministic identifier for the belief.
    * ``belief_type`` – classification/type of the belief.
    * ``description`` – concise description of the belief.
    * ``confidence`` – confidence matched from supporting pattern(s).
    * ``created_tick`` – world tick when the belief was first created.
    * ``updated_tick`` – world tick of the most recent update (same as created if stable).
    * ``supporting_pattern_ids`` – tuple of pattern IDs that support this belief.
    """

    belief_id: str
    belief_type: str
    description: str
    confidence: float
    created_tick: int
    updated_tick: int
    supporting_pattern_ids: Tuple[str, ...] = field(default_factory=tuple)
    validation_state: str = "STABLE"
    support_count: int = 0
    contradiction_count: int = 0
    last_validated_tick: int = 0


@dataclass(frozen=True)
class LearningState:
    """Container for deterministic learning observations.

    * ``observations`` – ordered tuple of ``LearningObservation`` entries.
    * ``learning_tick`` – the most recent tick for which observations were added.
    * ``total_observations`` – count of observations stored.
    """

    observations: Tuple[LearningObservation, ...] = field(default_factory=tuple)
    learning_tick: int = 0
    total_observations: int = 0
    patterns: Tuple[LearningPattern, ...] = field(default_factory=tuple)
    beliefs: Tuple[Belief, ...] = field(default_factory=tuple)
    @staticmethod
    def _observation_sort_key(obs: LearningObservation):
        # Deterministic ordering: tick ascending, then id lexicographically.
        return (obs.tick, obs.id)

    def add_observation(self, observation: LearningObservation) -> "LearningState":
        """Add a new ``LearningObservation`` if its ``id`` is not already present.

        Returns a new ``LearningState`` with the observation inserted in sorted order
        and ``total_observations`` updated.
        """
        if any(o.id == observation.id for o in self.observations):
            return self
        new_obs = tuple(sorted(self.observations + (observation,), key=self._observation_sort_key))
        return replace(self, observations=new_obs, total_observations=len(new_obs))

    def with_learning_tick(self, tick: int) -> "LearningState":
        """Return a copy with ``learning_tick`` updated to *tick*.
        """
        return replace(self, learning_tick=tick)

    def add_pattern(self, pattern: LearningPattern) -> "LearningState":
        """Add a new ``LearningPattern`` if its ``pattern_id`` is not already present.

        Returns a new ``LearningState`` with the pattern appended; patterns are kept
        in deterministic order by sorting on ``pattern_id``.
        """
        if any(p.pattern_id == pattern.pattern_id for p in self.patterns):
            return self
        # Append and sort for deterministic ordering.
        new_patterns = tuple(sorted(self.patterns + (pattern,), key=lambda p: p.pattern_id))
        return replace(self, patterns=new_patterns)

    def add_belief(self, belief: Belief) -> "LearningState":
        """Add a new ``Belief`` if its ``belief_id`` is not already present.

        Returns a new ``LearningState`` with the belief appended; beliefs are kept
        in deterministic order by sorting on ``belief_id``.
        """
        if any(b.belief_id == belief.belief_id for b in self.beliefs):
            return self
        new_beliefs = tuple(sorted(self.beliefs + (belief,), key=lambda b: b.belief_id))
        return replace(self, beliefs=new_beliefs)

    def replace_belief(self, belief: Belief) -> "LearningState":
        """Replace an existing belief (by belief_id) with a new version.

        If the belief does not exist, the state is unchanged.
        """
        if not any(b.belief_id == belief.belief_id for b in self.beliefs):
            return self
        new_beliefs = tuple(sorted((belief if b.belief_id == belief.belief_id else b for b in self.beliefs), key=lambda b: b.belief_id))
        return replace(self, beliefs=new_beliefs)
