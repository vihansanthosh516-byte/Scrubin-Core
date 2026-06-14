"""Append‑only deterministic store for ``Reflection`` objects.

Provides O(1) exact‑match lookup by statement and deterministic query ordering.
"""

from __future__ import annotations

from dataclasses import replace
from typing import List, Tuple, Optional

from .reflection import Reflection, deterministic_reflection_id, deterministic_reflection_hash


class ReflectionStore:
    """Deterministic, append‑only store for reflections.

    * ``_reflections`` – list preserving insertion order.
    * ``_index`` – maps statement strings to the reflection's list index for O(1) lookup.
    """

    def __init__(self) -> None:
        self._reflections: List[Reflection] = []
        self._index: dict[str, int] = {}

    # ---------------------------------------------------------------------
    # Core mutation – deterministic merging of supporting beliefs
    # ---------------------------------------------------------------------
    def add_or_update(self, reflection: Reflection) -> None:
        """Add a new reflection or merge with an existing one.

        Merges only when new supporting beliefs are present; otherwise, the existing
        reflection is left unchanged to preserve append‑only semantics on idempotent runs.
        """
        key = reflection.statement
        if key in self._index:
            idx = self._index[key]
            prior = self._reflections[idx]
            prior_set = set(prior.supporting_beliefs)
            incoming_set = set(reflection.supporting_beliefs)
            new_set = prior_set | incoming_set
            if new_set == prior_set:
                # No new beliefs – keep prior unchanged
                return
            added_count = len(new_set) - len(prior_set)
            # Approximate confidence of new beliefs as the incoming reflection's mean confidence
            total_conf = prior.confidence * prior.support_count + reflection.confidence * added_count
            new_support_count = len(new_set)
            new_confidence = total_conf / new_support_count if new_support_count > 0 else 0.0
            new_supporting = tuple(sorted(new_set))
            new_id = deterministic_reflection_id(prior.statement, new_supporting)
            merged = Reflection(
                id=new_id,
                statement=prior.statement,
                supporting_beliefs=new_supporting,
                support_count=new_support_count,
                confidence=new_confidence,
                first_seen_tick=min(prior.first_seen_tick, reflection.first_seen_tick),
                last_seen_tick=max(prior.last_seen_tick, reflection.last_seen_tick),
                replay_hash="",
            )
            merged = replace(merged, replay_hash=deterministic_reflection_hash(merged))
            self._reflections[idx] = merged
        else:
            # New reflection – assign deterministic id and hash.
            refl_id = deterministic_reflection_id(reflection.statement, reflection.supporting_beliefs)
            new_reflection = replace(reflection, id=refl_id)
            new_reflection = replace(new_reflection, replay_hash=deterministic_reflection_hash(new_reflection))
            self._reflections.append(new_reflection)
            self._index[key] = len(self._reflections) - 1

    # ---------------------------------------------------------------------
    # Query API – deterministic ordering, O(1) exact matches
    # ---------------------------------------------------------------------
    @property
    def reflections(self) -> Tuple[Reflection, ...]:
        """Immutable view of all stored reflections in insertion order."""
        return tuple(self._reflections)

    def query(
        self,
        statement: Optional[str] = None,
        min_confidence: Optional[float] = None,
        after_tick: Optional[int] = None,
    ) -> Tuple[Reflection, ...]:
        """Return reflections matching the supplied criteria.

        Parameters are optional – ``None`` means no filtering on that field.
        The result preserves the original deterministic insertion order.
        """
        result: List[Reflection] = []
        for r in self._reflections:
            if statement is not None and r.statement != statement:
                continue
            if min_confidence is not None and r.confidence < min_confidence:
                continue
            if after_tick is not None and r.last_seen_tick <= after_tick:
                continue
            result.append(r)
        return tuple(result)

    # ---------------------------------------------------------------------
    # Statistics helpers
    # ---------------------------------------------------------------------
    def reflection_count(self) -> int:
        return len(self._reflections)

    def mean_confidence(self) -> float:
        if not self._reflections:
            return 0.0
        total = sum(r.confidence for r in self._reflections)
        return total / len(self._reflections)

    def mean_support(self) -> float:
        if not self._reflections:
            return 0.0
        total = sum(r.support_count for r in self._reflections)
        return total / len(self._reflections)

    def max_support(self) -> int:
        if not self._reflections:
            return 0
        return max(r.support_count for r in self._reflections)

    def summary(self) -> Tuple[int, float, float, int]:
        """Return ``(count, mean_confidence, mean_support, max_support)``."""
        return (
            self.reflection_count(),
            self.mean_confidence(),
            self.mean_support(),
            self.max_support(),
        )
