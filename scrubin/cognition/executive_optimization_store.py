"""Append‑only deterministic store for ``ExecutiveOptimization`` objects.

Provides O(1) lookup, deterministic ordering, deterministic merge, and simple
statistics. No deletion, no mutation of existing entries.
"""

from __future__ import annotations

from dataclasses import replace
from typing import List, Tuple, Optional, Dict

from .executive_optimization import ExecutiveOptimization, deterministic_executive_optimization_hash


class ExecutiveOptimizationStore:
    """Deterministic, append‑only store for executive optimizations.

    * ``_optimizations`` – list preserving insertion order.
    * ``_index`` – maps optimization IDs to list indices for O(1) lookup.
    """

    def __init__(self) -> None:
        self._optimizations: List[ExecutiveOptimization] = []
        self._index: Dict[str, int] = {}

    # ---------------------------------------------------------------------
    # Core mutation – deterministic merging of duplicate optimizations
    # ---------------------------------------------------------------------
    def add_or_update(self, opt: ExecutiveOptimization) -> None:
        """Append a new optimization or merge with an existing one.

        Merge semantics (deterministic):
            * Union of ``supporting_profile_ids`` (sorted).
            * Union of ``supporting_bias_ids`` (sorted).
            * Keep higher ``optimization_score``.
            * Keep higher ``confidence``.
            * Update ``first_seen_tick`` to min, ``last_seen_tick`` to max.
        """
        if opt.id in self._index:
            idx = self._index[opt.id]
            prior = self._optimizations[idx]
            new_profile_ids = tuple(sorted(set(prior.supporting_profile_ids) | set(opt.supporting_profile_ids)))
            new_bias_ids = tuple(sorted(set(prior.supporting_bias_ids) | set(opt.supporting_bias_ids)))
            # Keep higher scores
            opt_score = max(prior.optimization_score, opt.optimization_score)
            opt_conf = max(prior.confidence, opt.confidence)
            merged = ExecutiveOptimization(
                id=prior.id,
                strategy_id=prior.strategy_id,
                optimization_score=opt_score,
                confidence=opt_conf,
                supporting_profile_ids=new_profile_ids,
                supporting_bias_ids=new_bias_ids,
                recommendation=prior.recommendation,  # recommendation stays the same (deterministic based on score)
                first_seen_tick=min(prior.first_seen_tick, opt.first_seen_tick),
                last_seen_tick=max(prior.last_seen_tick, opt.last_seen_tick),
                replay_hash="",
            )
            merged = replace(merged, replay_hash=deterministic_executive_optimization_hash(merged))
            self._optimizations[idx] = merged
        else:
            self._optimizations.append(opt)
            self._index[opt.id] = len(self._optimizations) - 1

    # ---------------------------------------------------------------------
    # Query API – deterministic ordering, O(1) exact matches
    # ---------------------------------------------------------------------
    @property
    def optimizations(self) -> Tuple[ExecutiveOptimization, ...]:
        """Immutable view of all stored optimizations in insertion order."""
        return tuple(self._optimizations)

    def query(self, strategy_id: Optional[str] = None) -> Tuple[ExecutiveOptimization, ...]:
        """Return optimizations matching the supplied criteria.

        Parameters are optional – ``None`` means no filtering.
        Result preserves deterministic insertion order.
        """
        result: List[ExecutiveOptimization] = []
        for o in self._optimizations:
            if strategy_id is not None and o.strategy_id != strategy_id:
                continue
            result.append(o)
        return tuple(result)

    # ---------------------------------------------------------------------
    # Statistics helpers
    # ---------------------------------------------------------------------
    def optimization_count(self) -> int:
        return len(self._optimizations)

    def mean_score(self) -> float:
        if not self._optimizations:
            return 0.0
        return sum(o.optimization_score for o in self._optimizations) / len(self._optimizations)

    def mean_confidence(self) -> float:
        if not self._optimizations:
            return 0.0
        return sum(o.confidence for o in self._optimizations) / len(self._optimizations)

    def summary(self) -> Tuple[int, float, float]:
        """Return ``(count, mean_score, mean_confidence)``.
        """
        return (
            self.optimization_count(),
            self.mean_score(),
            self.mean_confidence(),
        )
