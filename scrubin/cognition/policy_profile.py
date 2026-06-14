"""Immutable deterministic policy profile model.

Aggregates executive evaluations and recommendations for a given strategy.
All fields are immutable; updates are performed via ``replace``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from typing import Tuple


def deterministic_policy_profile_id(strategy_id: str) -> str:
    """Deterministic identifier for a ``PolicyProfile``.

    The ID is ``policyprof-`` plus the first 12 hex characters of a SHA‑256 hash
    over the canonical JSON representation of the ``strategy_id``.
    """
    canonical = json.dumps({"strategy_id": strategy_id}, separators=(",", ":"), sort_keys=True)
    return f"policyprof-{hashlib.sha256(canonical.encode()).hexdigest()[:12]}"


def deterministic_policy_profile_hash(profile: "PolicyProfile") -> str:
    """Deterministic replay hash for a fully populated ``PolicyProfile``.
    """
    data = {
        "id": profile.id,
        "strategy_id": profile.strategy_id,
        "executions": profile.executions,
        "success_count": profile.success_count,
        "failure_count": profile.failure_count,
        "average_score": profile.average_score,
        "confidence": profile.confidence,
        "recommendation_history": list(profile.recommendation_history),
        "supporting_evaluation_ids": list(profile.supporting_evaluation_ids),
        "first_seen_tick": profile.first_seen_tick,
        "last_seen_tick": profile.last_seen_tick,
    }
    json_repr = json.dumps(data, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(json_repr.encode()).hexdigest()


@dataclass(frozen=True)
class PolicyProfile:
    """Immutable profile aggregating evaluations for a specific strategy.

    ``executions`` – total number of executive evaluations observed.
    ``success_count`` and ``failure_count`` – derived from evaluation outcome scores.
    ``average_score`` – mean ``evaluation_score`` across executions.
    ``confidence`` – deterministic confidence score derived from success/failure.
    ``recommendation_history`` – tuple of recommendation strings (e.g., "continue").
    """
    id: str
    strategy_id: str
    executions: int
    success_count: int
    failure_count: int
    average_score: float
    confidence: float
    recommendation_history: Tuple[str, ...]
    supporting_evaluation_ids: Tuple[str, ...]
    first_seen_tick: int
    last_seen_tick: int
    replay_hash: str

    @staticmethod
    def create(
        strategy_id: str,
        executions: int = 0,
        success_count: int = 0,
        failure_count: int = 0,
        average_score: float = 0.0,
        confidence: float = 0.0,
        recommendation_history: Tuple[str, ...] = (),
        supporting_evaluation_ids: Tuple[str, ...] = (),
        first_seen_tick: int = 0,
        last_seen_tick: int = 0,
    ) -> "PolicyProfile":
        """Factory for a deterministic ``PolicyProfile``.

        The deterministic ``id`` is based solely on ``strategy_id``.
        """
        profile_id = deterministic_policy_profile_id(strategy_id)
        placeholder = PolicyProfile(
            id=profile_id,
            strategy_id=strategy_id,
            executions=executions,
            success_count=success_count,
            failure_count=failure_count,
            average_score=average_score,
            confidence=confidence,
            recommendation_history=recommendation_history,
            supporting_evaluation_ids=supporting_evaluation_ids,
            first_seen_tick=first_seen_tick,
            last_seen_tick=last_seen_tick,
            replay_hash="",
        )
        return replace(placeholder, replay_hash=deterministic_policy_profile_hash(placeholder))
