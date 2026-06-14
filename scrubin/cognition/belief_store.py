"""Append‑only deterministic store for ``Belief`` objects.

Provides O(1) exact‑match lookup by statement and deterministic query ordering.
"""

from __future__ import annotations

from dataclasses import replace
from typing import List, Tuple, Optional

from .belief import Belief, deterministic_belief_id, deterministic_belief_hash


class BeliefStore:
    """Deterministic, append‑only store for beliefs.

    * ``_beliefs`` – list of beliefs in insertion order.
    * ``_index`` – maps statement strings to the belief's list index.
    """

    def __init__(self) -> None:
        self._beliefs: List[Belief] = []
        self._index: dict[str, int] = {}

    # ---------------------------------------------------------------------
    # Core mutation – deterministic merging of supporting facts
    # ---------------------------------------------------------------------
    def add_or_update(self, belief: Belief) -> None:
        """Add a new belief or merge with an existing one.

        Merging updates ``support_count``, ``supporting_facts`` (appended),
        ``first_seen_tick``, ``last_seen_tick`` and recomputes ``confidence`` as
        the mean of the supporting fact confidences.
        """
        key = belief.statement
        if key in self._index:
            idx = self._index[key]
            prior = self._beliefs[idx]
            # Merge using the Belief.create helper (which computes new confidence).
            merged = Belief.create(
                statement=prior.statement,
                fact_id=belief.supporting_facts[0],
                fact_confidence=belief.confidence,
                tick=belief.last_seen_tick,
                prior=prior,
            )
            # Preserve deterministic ordering – replace in place.
            self._beliefs[idx] = merged
        else:
            # New belief – assign deterministic id if not provided and compute hash.
            if belief.id:
                belief_id = belief.id
                new_belief = replace(belief, id=belief_id)
            else:
                belief_id = deterministic_belief_id(belief.statement, belief.supporting_facts)
                new_belief = replace(belief, id=belief_id)
            new_belief = replace(new_belief, replay_hash=deterministic_belief_hash(new_belief))
            self._beliefs.append(new_belief)
            self._index[key] = len(self._beliefs) - 1

    # ---------------------------------------------------------------------
    # Query API – deterministic ordering, O(1) exact matches
    # ---------------------------------------------------------------------
    @property
    def beliefs(self) -> Tuple[Belief, ...]:
        """Immutable view of all stored beliefs in insertion order."""
        return tuple(self._beliefs)

    def query(
        self,
        statement: Optional[str] = None,
        min_confidence: Optional[float] = None,
        after_tick: Optional[int] = None,
    ) -> Tuple[Belief, ...]:
        """Return beliefs matching the supplied criteria.

        Parameters are optional; ``None`` means no filtering on that field.
        The result preserves the original deterministic insertion order.
        """
        result: List[Belief] = []
        for b in self._beliefs:
            if statement is not None and b.statement != statement:
                continue
            if min_confidence is not None and b.confidence < min_confidence:
                continue
            if after_tick is not None and b.last_seen_tick <= after_tick:
                continue
            result.append(b)
        return tuple(result)

    # ---------------------------------------------------------------------
    # Statistics helpers
    # ---------------------------------------------------------------------
    def belief_count(self) -> int:
        return len(self._beliefs)

    def mean_confidence(self) -> float:
        if not self._beliefs:
            return 0.0
        total = sum(b.confidence for b in self._beliefs)
        return total / len(self._beliefs)

    def summary(self) -> Tuple[int, float]:
        """Return ``(belief_count, mean_confidence)`` for quick reporting."""
        return (self.belief_count(), self.mean_confidence())
