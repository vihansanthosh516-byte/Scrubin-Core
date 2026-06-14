"""Append‑only deterministic store for ``Strategy`` objects.

Provides O(1) lookup by strategy ID and deterministic query ordering.
"""

from __future__ import annotations

from dataclasses import replace
from typing import List, Tuple, Optional, Dict

from .strategy import Strategy, deterministic_strategy_hash


class StrategyStore:
    """Deterministic, append‑only store for reusable strategies.

    * ``_strategies`` – list preserving insertion order.
    * ``_index`` – maps strategy IDs to list indices for O(1) lookup.
    """

    def __init__(self) -> None:
        self._strategies: List[Strategy] = []
        self._index: Dict[str, int] = {}

    # ---------------------------------------------------------------------
    # Core mutation – deterministic merging of duplicate strategies
    # ---------------------------------------------------------------------
    def add_or_update(self, strategy: Strategy) -> None:
        """Append a new strategy or merge with an existing one.

        On duplicate IDs the supporting plan IDs are merged (union, sorted) and the
        ``success_count``, ``failure_count`` are summed. ``first_seen_tick`` is the
        minimum of the two, ``last_seen_tick`` the maximum. Confidence is
        recomputed using the deterministic formula.
        """
        if strategy.id in self._index:
            idx = self._index[strategy.id]
            prior = self._strategies[idx]
            # Merge supporting plans
            new_plans = tuple(sorted(set(prior.supporting_plan_ids) | set(strategy.supporting_plan_ids)))
            # Aggregate counts
            new_success = prior.success_count + strategy.success_count
            new_failure = prior.failure_count + strategy.failure_count
            # Recalculate confidence deterministically
            conf = (new_success + 1) / (new_success + new_failure + 2) if (new_success + new_failure + 2) > 0 else 0.0
            merged = Strategy(
                id=prior.id,
                name=prior.name,
                description=prior.description,
                trigger_conditions=prior.trigger_conditions,
                action_sequence=prior.action_sequence,
                success_count=new_success,
                failure_count=new_failure,
                confidence=conf,
                supporting_plan_ids=new_plans,
                first_seen_tick=min(prior.first_seen_tick, strategy.first_seen_tick),
                last_seen_tick=max(prior.last_seen_tick, strategy.last_seen_tick),
                replay_hash="",
            )
            merged = replace(merged, replay_hash=deterministic_strategy_hash(merged))
            self._strategies[idx] = merged
        else:
            self._strategies.append(strategy)
            self._index[strategy.id] = len(self._strategies) - 1

    # ---------------------------------------------------------------------
    # Query API – deterministic ordering, O(1) exact matches
    # ---------------------------------------------------------------------
    @property
    def strategies(self) -> Tuple[Strategy, ...]:
        """Immutable view of all stored strategies in insertion order."""
        return tuple(self._strategies)

    def query(
        self,
        name: Optional[str] = None,
        min_confidence: Optional[float] = None,
        after_tick: Optional[int] = None,
    ) -> Tuple[Strategy, ...]:
        """Return strategies matching the supplied criteria.

        Parameters are optional – ``None`` means no filtering on that field.
        The result preserves the original deterministic insertion order.
        """
        result: List[Strategy] = []
        for s in self._strategies:
            if name is not None and s.name != name:
                continue
            if min_confidence is not None and s.confidence < min_confidence:
                continue
            if after_tick is not None and s.last_seen_tick <= after_tick:
                continue
            result.append(s)
        return tuple(result)

    # ---------------------------------------------------------------------
    # Statistics helpers
    # ---------------------------------------------------------------------
    def strategy_count(self) -> int:
        return len(self._strategies)

    def mean_confidence(self) -> float:
        if not self._strategies:
            return 0.0
        return sum(s.confidence for s in self._strategies) / len(self._strategies)

    def max_confidence(self) -> float:
        if not self._strategies:
            return 0.0
        return max(s.confidence for s in self._strategies)

    def mean_support(self) -> float:
        if not self._strategies:
            return 0.0
        total = sum(len(s.supporting_plan_ids) for s in self._strategies)
        return total / len(self._strategies)

    def summary(self) -> Tuple[int, float, float, float]:
        """Return ``(count, mean_confidence, max_confidence, mean_support)``."""
        return (
            self.strategy_count(),
            self.mean_confidence(),
            self.max_confidence(),
            self.mean_support(),
        )
