"""Append‑only deterministic store for ``PolicyProfile`` objects.

Provides O(1) lookup by profile ID, deterministic insertion order, and deterministic
merge semantics for duplicate IDs.
"""

from __future__ import annotations

from dataclasses import replace
from typing import List, Tuple, Optional, Dict

from .policy_profile import PolicyProfile, deterministic_policy_profile_hash


class PolicyStore:
    """Deterministic, append‑only store for policy profiles.

    * ``_profiles`` – list preserving insertion order.
    * ``_index`` – maps profile IDs to list indices for O(1) lookup.
    """

    def __init__(self) -> None:
        self._profiles: List[PolicyProfile] = []
        self._index: Dict[str, int] = {}

    # ---------------------------------------------------------------------
    # Core mutation – deterministic merging of duplicate profiles
    # ---------------------------------------------------------------------
    def add_or_update(self, profile: PolicyProfile) -> None:
        """Append a new profile or merge with an existing one.

        Merge semantics:
            * ``executions`` – summed.
            * ``success_count``, ``failure_count`` – summed.
            * ``average_score`` – weighted mean by executions.
            * ``confidence`` – recomputed via deterministic formula:
              ``(success+1)/(success+failure+2)``.
            * ``recommendation_history`` – union (sorted) of prior and new.
            * ``supporting_evaluation_ids`` – union (sorted).
            * ``first_seen_tick`` – min of both.
            * ``last_seen_tick`` – max of both.
        """
        if profile.id in self._index:
            idx = self._index[profile.id]
            prior = self._profiles[idx]
            # Merge counts
            total_executions = prior.executions + profile.executions
            total_success = prior.success_count + profile.success_count
            total_failure = prior.failure_count + profile.failure_count
            # Weighted average score
            if total_executions > 0:
                avg_score = (
                    (prior.average_score * prior.executions) + (profile.average_score * profile.executions)
                ) / total_executions
            else:
                avg_score = 0.0
            # Recompute confidence deterministically
            conf = (total_success + 1) / (total_success + total_failure + 2) if (total_success + total_failure + 2) > 0 else 0.0
            # Union recommendation history (sorted, unique)
            new_recs = tuple(sorted(set(prior.recommendation_history) | set(profile.recommendation_history)))
            # Union supporting evaluation IDs
            new_evals = tuple(sorted(set(prior.supporting_evaluation_ids) | set(profile.supporting_evaluation_ids)))
            merged = PolicyProfile(
                id=prior.id,
                strategy_id=prior.strategy_id,
                executions=total_executions,
                success_count=total_success,
                failure_count=total_failure,
                average_score=avg_score,
                confidence=conf,
                recommendation_history=new_recs,
                supporting_evaluation_ids=new_evals,
                first_seen_tick=min(prior.first_seen_tick, profile.first_seen_tick),
                last_seen_tick=max(prior.last_seen_tick, profile.last_seen_tick),
                replay_hash="",
            )
            merged = replace(merged, replay_hash=deterministic_policy_profile_hash(merged))
            self._profiles[idx] = merged
        else:
            self._profiles.append(profile)
            self._index[profile.id] = len(self._profiles) - 1

    # ---------------------------------------------------------------------
    # Query API – deterministic ordering, O(1) exact matches
    # ---------------------------------------------------------------------
    @property
    def profiles(self) -> Tuple[PolicyProfile, ...]:
        """Immutable view of all stored policy profiles in insertion order."""
        return tuple(self._profiles)

    def query(
        self,
        strategy_id: Optional[str] = None,
        min_confidence: Optional[float] = None,
        after_tick: Optional[int] = None,
    ) -> Tuple[PolicyProfile, ...]:
        """Return profiles matching supplied criteria.

        Parameters are optional – ``None`` means no filtering on that field.
        Result preserves deterministic insertion order.
        """
        result: List[PolicyProfile] = []
        for p in self._profiles:
            if strategy_id is not None and p.strategy_id != strategy_id:
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
    def profile_count(self) -> int:
        return len(self._profiles)

    def mean_confidence(self) -> float:
        if not self._profiles:
            return 0.0
        return sum(p.confidence for p in self._profiles) / len(self._profiles)

    def mean_average_score(self) -> float:
        if not self._profiles:
            return 0.0
        return sum(p.average_score for p in self._profiles) / len(self._profiles)

    def summary(self) -> Tuple[int, float, float]:
        """Return ``(count, mean_confidence, mean_average_score)``.
        """
        return (
            self.profile_count(),
            self.mean_confidence(),
            self.mean_average_score(),
        )
