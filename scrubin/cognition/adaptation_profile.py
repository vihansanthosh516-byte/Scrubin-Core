"""Immutable deterministic adaptation profile model.

Aggregates executive feedback over time for a specific strategy, providing a
persistent memory of how effective adaptations have been.
All fields are frozen; updates use ``replace``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from typing import Tuple


def deterministic_adaptation_profile_id(strategy_id: str) -> str:
    """Deterministic identifier for an ``AdaptationProfile``.

    The ID is ``adaptprofile-`` plus the first 12 hex characters of a SHA‑256 hash
    over a canonical JSON representation of the ``strategy_id``. The ID is
    independent of ticks to allow merging across time.
    """
    canonical = json.dumps({"strategy_id": strategy_id}, separators=(",", ":"), sort_keys=True)
    return f"adaptprofile-{hashlib.sha256(canonical.encode()).hexdigest()[:12]}"


def deterministic_adaptation_profile_hash(profile: "AdaptationProfile") -> str:
    """Deterministic replay hash for a fully populated ``AdaptationProfile``.
    """
    data = {
        "id": profile.id,
        "strategy_id": profile.strategy_id,
        "executions": profile.executions,
        "successful_adaptations": profile.successful_adaptations,
        "failed_adaptations": profile.failed_adaptations,
        "average_delta": profile.average_delta,
        "confidence": profile.confidence,
        "supporting_feedback_ids": list(profile.supporting_feedback_ids),
        "supporting_policy_ids": list(profile.supporting_policy_ids),
        "first_seen_tick": profile.first_seen_tick,
        "last_seen_tick": profile.last_seen_tick,
    }
    json_repr = json.dumps(data, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(json_repr.encode()).hexdigest()


@dataclass(frozen=True)
class AdaptationProfile:
    """Immutable aggregation of executive adaptation feedback for a strategy.

    ``executions`` – total number of feedback entries observed.
    ``successful_adaptations`` – count where ``confidence_delta`` > 0.
    ``failed_adaptations`` – count where ``confidence_delta`` <= 0.
    ``average_delta`` – mean ``confidence_delta`` across executions.
    ``confidence`` – Laplace‑smoothed success probability
        ``(successful_adaptations + 1) / (successful_adaptations + failed_adaptations + 2)``.
    """
    id: str
    strategy_id: str
    executions: int
    successful_adaptations: int
    failed_adaptations: int
    average_delta: float
    confidence: float
    supporting_feedback_ids: Tuple[str, ...]
    supporting_policy_ids: Tuple[str, ...]
    first_seen_tick: int
    last_seen_tick: int
    replay_hash: str

    @staticmethod
    def create(
        strategy_id: str,
        executions: int = 0,
        successful_adaptations: int = 0,
        failed_adaptations: int = 0,
        average_delta: float = 0.0,
        confidence: float = 0.0,
        supporting_feedback_ids: Tuple[str, ...] = (),
        supporting_policy_ids: Tuple[str, ...] = (),
        first_seen_tick: int = 0,
        last_seen_tick: int = 0,
    ) -> "AdaptationProfile":
        """Factory that creates a deterministic ``AdaptationProfile``.

        ``id`` is derived solely from ``strategy_id``.
        """
        profile_id = deterministic_adaptation_profile_id(strategy_id)
        placeholder = AdaptationProfile(
            id=profile_id,
            strategy_id=strategy_id,
            executions=executions,
            successful_adaptations=successful_adaptations,
            failed_adaptations=failed_adaptations,
            average_delta=average_delta,
            confidence=confidence,
            supporting_feedback_ids=supporting_feedback_ids,
            supporting_policy_ids=supporting_policy_ids,
            first_seen_tick=first_seen_tick,
            last_seen_tick=last_seen_tick,
            replay_hash="",
        )
        return replace(placeholder, replay_hash=deterministic_adaptation_profile_hash(placeholder))
