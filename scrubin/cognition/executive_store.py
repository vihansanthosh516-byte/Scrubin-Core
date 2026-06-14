"""Append‑only deterministic store for ``ExecutiveGoal`` objects.

Provides O(1) lookup by goal ID and deterministic query ordering.
"""

from __future__ import annotations

from dataclasses import replace
from typing import List, Tuple, Optional

from .executive_goal import ExecutiveGoal, deterministic_executive_goal_hash


class ExecutiveStore:
    """Deterministic, append‑only store for executive goals.

    * ``_goals`` – list preserving insertion order.
    * ``_index`` – maps goal IDs to the goal's list index for O(1) lookup.
    """

    def __init__(self) -> None:
        self._goals: List[ExecutiveGoal] = []
        self._index: dict[str, int] = {}

    # ---------------------------------------------------------------------
    # Core mutation – deterministic merging of duplicate goals
    # ---------------------------------------------------------------------
    def add_or_update(self, goal: ExecutiveGoal) -> None:
        """Append a new goal or merge with an existing one.

        On duplicate IDs, supporting patterns and beliefs are merged (union,
        sorted) and the newer ``priority``, ``confidence`` and ``status`` are
        applied. The ``created_tick`` and ``description`` are retained from the
        original goal.
        """
        if goal.id in self._index:
            idx = self._index[goal.id]
            prior = self._goals[idx]
            new_patterns = tuple(sorted(set(prior.supporting_patterns) | set(goal.supporting_patterns)))
            new_beliefs = tuple(sorted(set(prior.supporting_beliefs) | set(goal.supporting_beliefs)))
            merged = ExecutiveGoal(
                id=prior.id,
                description=prior.description,
                priority=goal.priority,
                confidence=goal.confidence,
                status=goal.status,
                supporting_patterns=new_patterns,
                supporting_beliefs=new_beliefs,
                created_tick=prior.created_tick,
                replay_hash="",
            )
            merged = replace(merged, replay_hash=deterministic_executive_goal_hash(merged))
            self._goals[idx] = merged
        else:
            self._goals.append(goal)
            self._index[goal.id] = len(self._goals) - 1

    # ---------------------------------------------------------------------
    # Query API – deterministic ordering, O(1) exact matches
    # ---------------------------------------------------------------------
    @property
    def goals(self) -> Tuple[ExecutiveGoal, ...]:
        """Immutable view of all stored goals in insertion order."""
        return tuple(self._goals)

    def query(
        self,
        status: Optional[str] = None,
        min_priority: Optional[float] = None,
        after_tick: Optional[int] = None,
    ) -> Tuple[ExecutiveGoal, ...]:
        """Return goals matching the supplied criteria.

        Parameters are optional – ``None`` means no filtering on that field.
        The result preserves the original deterministic insertion order.
        """
        result: List[ExecutiveGoal] = []
        for g in self._goals:
            if status is not None and g.status != status:
                continue
            if min_priority is not None and g.priority < min_priority:
                continue
            if after_tick is not None and g.created_tick <= after_tick:
                continue
            result.append(g)
        return tuple(result)

    # ---------------------------------------------------------------------
    # Statistics helpers
    # ---------------------------------------------------------------------
    def goal_count(self) -> int:
        return len(self._goals)

    def mean_priority(self) -> float:
        if not self._goals:
            return 0.0
        return sum(g.priority for g in self._goals) / len(self._goals)

    def max_priority(self) -> float:
        if not self._goals:
            return 0.0
        return max(g.priority for g in self._goals)

    def mean_confidence(self) -> float:
        if not self._goals:
            return 0.0
        return sum(g.confidence for g in self._goals) / len(self._goals)

    def status_counts(self) -> dict:
        counts = {"pending": 0, "active": 0, "completed": 0, "failed": 0, "cancelled": 0}
        for g in self._goals:
            counts[g.status] = counts.get(g.status, 0) + 1
        return counts

    def summary(self) -> Tuple[int, float, float, float, dict]:
        """Return ``(count, mean_priority, max_priority, mean_confidence, status_counts)``."""
        return (
            self.goal_count(),
            self.mean_priority(),
            self.max_priority(),
            self.mean_confidence(),
            self.status_counts(),
        )
