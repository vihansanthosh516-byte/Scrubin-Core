"""Append‑only deterministic store for ``AdaptationProfile`` objects.

Provides O(1) lookup, deterministic insertion order, deterministic merge and
statistics. No deletion, no mutation of existing profiles.
"""

from __future__ import annotations

from dataclasses import replace
from typing import List, Tuple, Optional, Dict

from .adaptation_profile import AdaptationProfile, deterministic_adaptation_profile_hash


class AdaptationStore:
    """Deterministic, append‑only store for adaptation profiles.

    * ``_profiles`` – list preserving insertion order.
    * ``_index`` – maps profile IDs to list indices for O(1) lookup.
    """

    def __init__(self) -> None:
        self._profiles: List[AdaptationProfile] = []
        self._index: Dict[str, int] = {}

    # ---------------------------------------------------------------------
    # Core mutation – deterministic merging of duplicate profiles
    # ---------------------------------------------------------------------
    def add_or_update(self, profile: AdaptationProfile) -> None:
        """Append a new profile or merge with an existing one.

        Merge semantics (deterministic):
            * ``executions`` – summed.
            * ``successful_adaptations`` – summed.
            * ``failed_adaptations`` – summed.
            * ``average_delta`` – weighted mean by executions.
            * ``confidence`` – recomputed using Laplace smoothing based on the
              merged success/failure counts.
            * ``supporting_feedback_ids`` – union (sorted).
            * ``supporting_policy_ids`` – union (sorted).
            * ``first_seen_tick`` – min of the two.
            * ``last_seen_tick`` – max of the two.
        """
        if profile.id in self._index:
            idx = self._index[profile.id]
            prior = self._profiles[idx]
            total_executions = prior.executions + profile.executions
            total_success = prior.successful_adaptations + profile.successful_adaptations
            total_failure = prior.failed_adaptations + profile.failed_adaptations
            # Weighted average delta
            if total_executions > 0:
                avg_delta = (
                    prior.average_delta * prior.executions + profile.average_delta * profile.executions
                ) / total_executions
            else:
                avg_delta = 0.0
            # Recompute confidence with Laplace smoothing
            conf = (total_success + 1) / (total_success + total_failure + 2) if (total_success + total_failure + 2) > 0 else 0.0
            # Union supporting IDs
            new_feedback = tuple(sorted(set(prior.supporting_feedback_ids) | set(profile.supporting_feedback_ids)))
            new_policy = tuple(sorted(set(prior.supporting_policy_ids) | set(profile.supporting_policy_ids)))
            merged = AdaptationProfile(
                id=prior.id,
                strategy_id=prior.strategy_id,
                executions=total_executions,
                successful_adaptations=total_success,
                failed_adaptations=total_failure,
                average_delta=avg_delta,
                confidence=conf,
                supporting_feedback_ids=new_feedback,
                supporting_policy_ids=new_policy,
                first_seen_tick=min(prior.first_seen_tick, profile.first_seen_tick),
                last_seen_tick=max(prior.last_seen_tick, profile.last_seen_tick),
                replay_hash="",
            )
            merged = replace(merged, replay_hash=deterministic_adaptation_profile_hash(merged))
            self._profiles[idx] = merged
        else:
            self._profiles.append(profile)
            self._index[profile.id] = len(self._profiles) - 1

    # ---------------------------------------------------------------------
    # Query API – deterministic ordering, O(1) exact matches
    # ---------------------------------------------------------------------
    @property
    def profiles(self) -> Tuple[AdaptationProfile, ...]:
        """Immutable view of all stored adaptation profiles in insertion order."""
        return tuple(self._profiles)

    def query(self, strategy_id: Optional[str] = None) -> Tuple[AdaptationProfile, ...]:
        """Return profiles matching supplied criteria.

        Parameters are optional – ``None`` means no filtering.
        Result preserves deterministic insertion order.
        """
        result: List[AdaptationProfile] = []
        for p in self._profiles:
            if strategy_id is not None and p.strategy_id != strategy_id:
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

    def mean_average_delta(self) -> float:
        if not self._profiles:
            return 0.0
        return sum(p.average_delta for p in self._profiles) / len(self._profiles)

    def summary(self) -> Tuple[int, float, float]:
        """Return ``(count, mean_confidence, mean_average_delta)``.
        """
        return (
            self.profile_count(),
            self.mean_confidence(),
            self.mean_average_delta(),
        )
