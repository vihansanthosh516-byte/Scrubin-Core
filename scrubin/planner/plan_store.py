"""Append‑only deterministic store for ``Plan`` objects.

Provides O(1) exact‑match lookup by plan ID and deterministic query ordering.
"""

from __future__ import annotations

from dataclasses import replace
from typing import List, Tuple, Optional

from .plan import Plan


class PlanStore:
    """Immutable, append‑only store for deterministic plans.

    * ``_plans`` – list preserving insertion order.
    * ``_index`` – maps plan IDs to the plan's list index for O(1) lookup.
    """

    def __init__(self) -> None:
        self._plans: List[Plan] = []
        self._index: dict[str, int] = {}

    # ---------------------------------------------------------------------
    # Core mutation – deterministic append‑only semantics
    # ---------------------------------------------------------------------
    def add(self, plan: Plan) -> None:
        """Append a new plan to the store.

        Duplicate IDs are ignored – the store respects the first occurrence.
        """
        if plan.id in self._index:
            return
        self._plans.append(plan)
        self._index[plan.id] = len(self._plans) - 1

    @property
    def plans(self) -> Tuple[Plan, ...]:
        """Immutable view of all stored plans in insertion order."""
        return tuple(self._plans)

    def query(
        self,
        min_score: Optional[float] = None,
        after_tick: Optional[int] = None,
    ) -> Tuple[Plan, ...]:
        """Return plans matching the supplied criteria.

        Parameters are optional – ``None`` means no filtering on that field.
        The result preserves original deterministic insertion order.
        """
        result: List[Plan] = []
        for p in self._plans:
            if min_score is not None and p.total_score < min_score:
                continue
            if after_tick is not None and p.root_tick <= after_tick:
                continue
            result.append(p)
        return tuple(result)

    # ---------------------------------------------------------------------
    # Statistics helpers
    # ---------------------------------------------------------------------
    def plan_count(self) -> int:
        return len(self._plans)

    def mean_score(self) -> float:
        if not self._plans:
            return 0.0
        return sum(p.total_score for p in self._plans) / len(self._plans)

    def max_score(self) -> float:
        if not self._plans:
            return 0.0
        return max(p.total_score for p in self._plans)

    def mean_confidence(self) -> float:
        if not self._plans:
            return 0.0
        return sum(p.confidence for p in self._plans) / len(self._plans)

    def average_horizon(self) -> float:
        if not self._plans:
            return 0.0
        return sum(p.horizon for p in self._plans) / len(self._plans)

    def summary(self) -> Tuple[int, float, float, float, float]:
        """Return ``(count, mean_score, max_score, mean_confidence, avg_horizon)``."""
        return (
            self.plan_count(),
            self.mean_score(),
            self.max_score(),
            self.mean_confidence(),
            self.average_horizon(),
        )
