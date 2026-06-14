"""Append‑only deterministic store for ``BiasPlanCandidate`` objects.

Provides O(1) lookup, deterministic merge semantics, query API and simple
statistics. No mutation of existing candidates – updates are performed via
``add_or_update`` which returns a new immutable object.
"""

from __future__ import annotations

from dataclasses import replace
from typing import List, Tuple, Optional, Dict

from .bias_plan_candidate import BiasPlanCandidate, deterministic_bias_plan_candidate_hash


class BiasPlanStore:
    """Deterministic, append‑only store for bias‑aware plan candidates.

    * ``_candidates`` – list preserving insertion order.
    * ``_index`` – maps candidate IDs to list indices for O(1) lookup.
    """

    def __init__(self) -> None:
        self._candidates: List[BiasPlanCandidate] = []
        self._index: Dict[str, int] = {}

    # ---------------------------------------------------------------------
    # Core mutation – deterministic merging of duplicate candidates
    # ---------------------------------------------------------------------
    def add_or_update(self, candidate: BiasPlanCandidate) -> None:
        """Append a new candidate or merge with an existing one.

        Merge semantics (deterministic):
            * Union of ``supporting_policy_ids`` (sorted).
            * Union of ``supporting_strategy_ids`` (sorted).
            * Union of ``supporting_goal_ids`` (sorted).
            * ``base_score`` – keep higher of the two.
            * ``bias_score`` – keep higher of the two.
            * ``final_score`` – keep higher of the two.
            * ``replay_hash`` recomputed.
        """
        if candidate.id in self._index:
            idx = self._index[candidate.id]
            prior = self._candidates[idx]
            # Merge supporting IDs (union, sorted)
            new_policy = tuple(sorted(set(prior.supporting_policy_ids) | set(candidate.supporting_policy_ids)))
            new_strategy = tuple(sorted(set(prior.supporting_strategy_ids) | set(candidate.supporting_strategy_ids)))
            new_goal = tuple(sorted(set(prior.supporting_goal_ids) | set(candidate.supporting_goal_ids)))
            # Keep highest scores
            base_score = max(prior.base_score, candidate.base_score)
            bias_score = max(prior.bias_score, candidate.bias_score)
            final_score = max(prior.final_score, candidate.final_score)
            merged = BiasPlanCandidate(
                id=prior.id,
                goal_id=prior.goal_id,
                strategy_id=prior.strategy_id,
                base_score=base_score,
                bias_score=bias_score,
                final_score=final_score,
                supporting_policy_ids=new_policy,
                supporting_strategy_ids=new_strategy,
                supporting_goal_ids=new_goal,
                replay_hash="",
            )
            merged = replace(merged, replay_hash=deterministic_bias_plan_candidate_hash(merged))
            self._candidates[idx] = merged
        else:
            self._candidates.append(candidate)
            self._index[candidate.id] = len(self._candidates) - 1

    # ---------------------------------------------------------------------
    # Query API – deterministic ordering, O(1) exact matches
    # ---------------------------------------------------------------------
    @property
    def candidates(self) -> Tuple[BiasPlanCandidate, ...]:
        """Immutable view of all stored candidates in insertion order."""
        return tuple(self._candidates)

    def query(
        self,
        goal_id: Optional[str] = None,
        strategy_id: Optional[str] = None,
        min_final_score: Optional[float] = None,
    ) -> Tuple[BiasPlanCandidate, ...]:
        """Return candidates matching supplied criteria.

        Parameters are optional – ``None`` means no filtering on that field.
        Result preserves deterministic insertion order.
        """
        result: List[BiasPlanCandidate] = []
        for c in self._candidates:
            if goal_id is not None and c.goal_id != goal_id:
                continue
            if strategy_id is not None and c.strategy_id != strategy_id:
                continue
            if min_final_score is not None and c.final_score < min_final_score:
                continue
            result.append(c)
        return tuple(result)

    # ---------------------------------------------------------------------
    # Statistics helpers
    # ---------------------------------------------------------------------
    def candidate_count(self) -> int:
        return len(self._candidates)

    def mean_final_score(self) -> float:
        if not self._candidates:
            return 0.0
        return sum(c.final_score for c in self._candidates) / len(self._candidates)

    def mean_bias_score(self) -> float:
        if not self._candidates:
            return 0.0
        return sum(c.bias_score for c in self._candidates) / len(self._candidates)

    def summary(self) -> Tuple[int, float, float]:
        """Return ``(count, mean_final_score, mean_bias_score)``."""
        return (
            self.candidate_count(),
            self.mean_final_score(),
            self.mean_bias_score(),
        )
