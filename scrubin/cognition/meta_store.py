"""Append‑only deterministic store for ``MetaPattern`` objects.

Provides O(1) exact‑match lookup by statement and deterministic query ordering.
"""

from __future__ import annotations

from dataclasses import replace
from typing import List, Tuple, Optional

from .meta_pattern import MetaPattern, deterministic_meta_pattern_id, deterministic_meta_pattern_hash


class MetaStore:
    """Deterministic, append‑only store for meta‑patterns.

    * ``_patterns`` – list preserving insertion order.
    * ``_index`` – maps statement strings to the pattern's list index for O(1) lookup.
    """

    def __init__(self) -> None:
        self._patterns: List[MetaPattern] = []
        self._index: dict[str, int] = {}

    # ---------------------------------------------------------------------
    # Core mutation – deterministic merging of supporting evidence
    # ---------------------------------------------------------------------
    def add_or_update(self, pattern: MetaPattern) -> None:
        """Add a new pattern or merge with an existing one.

        Merging updates ``support_count``, ``supporting_reflections``, ``supporting_counterfactuals``,
        ``first_seen_tick``, ``last_seen_tick`` and recomputes ``confidence`` as a weighted mean
        based on the supporting counts.
        """
        key = pattern.statement
        if key in self._index:
            idx = self._index[key]
            prior = self._patterns[idx]
            # Merge supporting sets
            new_reflections = tuple(sorted(set(prior.supporting_reflections) | set(pattern.supporting_reflections)))
            new_counterfactuals = tuple(sorted(set(prior.supporting_counterfactuals) | set(pattern.supporting_counterfactuals)))
            new_support_count = prior.support_count + pattern.support_count
            # Weighted confidence
            total_conf = prior.confidence * prior.support_count + pattern.confidence * pattern.support_count
            new_confidence = total_conf / new_support_count if new_support_count > 0 else 0.0
            new_first = min(prior.first_seen_tick, pattern.first_seen_tick)
            new_last = max(prior.last_seen_tick, pattern.last_seen_tick)
            new_id = deterministic_meta_pattern_id(key, new_reflections, new_counterfactuals)
            merged = MetaPattern(
                id=new_id,
                statement=key,
                confidence=new_confidence,
                support_count=new_support_count,
                supporting_reflections=new_reflections,
                supporting_counterfactuals=new_counterfactuals,
                first_seen_tick=new_first,
                last_seen_tick=new_last,
                replay_hash="",
            )
            merged = replace(merged, replay_hash=deterministic_meta_pattern_hash(merged))
            self._patterns[idx] = merged
        else:
            # New pattern – assign deterministic id if not already set (id is already deterministic in factory)
            self._patterns.append(pattern)
            self._index[key] = len(self._patterns) - 1

    # ---------------------------------------------------------------------
    # Query API – deterministic ordering, O(1) exact matches
    # ---------------------------------------------------------------------
    @property
    def patterns(self) -> Tuple[MetaPattern, ...]:
        """Immutable view of all stored patterns in insertion order."""
        return tuple(self._patterns)

    def query(
        self,
        statement: Optional[str] = None,
        min_confidence: Optional[float] = None,
        after_tick: Optional[int] = None,
    ) -> Tuple[MetaPattern, ...]:
        """Return patterns matching the supplied criteria.

        Parameters are optional – ``None`` means no filtering on that field.
        The result preserves the original deterministic insertion order.
        """
        result: List[MetaPattern] = []
        for p in self._patterns:
            if statement is not None and p.statement != statement:
                continue
            if min_confidence is not None and p.confidence < min_confidence:
                continue
            if after_tick is not None and p.last_seen_tick <= after_tick:
                continue
            result.append(p)
        return tuple(result)

    # ---------------------------------------------------------------------
    # Statistics helpers
    # ---------------------------------------------------------------------
    def pattern_count(self) -> int:
        return len(self._patterns)

    def mean_confidence(self) -> float:
        if not self._patterns:
            return 0.0
        total = sum(p.confidence for p in self._patterns)
        return total / len(self._patterns)

    def max_confidence(self) -> float:
        if not self._patterns:
            return 0.0
        return max(p.confidence for p in self._patterns)

    def mean_support(self) -> float:
        if not self._patterns:
            return 0.0
        total = sum(p.support_count for p in self._patterns)
        return total / len(self._patterns)

    def total_support(self) -> int:
        return sum(p.support_count for p in self._patterns)

    def summary(self) -> Tuple[int, float, float, float, int]:
        """Return ``(count, mean_confidence, max_confidence, mean_support, total_support)``."""
        return (
            self.pattern_count(),
            self.mean_confidence(),
            self.max_confidence(),
            self.mean_support(),
            self.total_support(),
        )
