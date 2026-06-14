"""Immutable deterministic executive optimization model.

Aggregates long‑term adaptation and policy confidence to produce a persistent
optimization record for each strategy. All fields are frozen; updates are done
via ``replace``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from typing import Tuple


def deterministic_executive_optimization_id(strategy_id: str) -> str:
    """Deterministic identifier for an ``ExecutiveOptimization``.

    The ID is ``opt-`` plus the first 12 hex characters of a SHA‑256 hash over a
    canonical JSON representation of the ``strategy_id``.
    """
    canonical = json.dumps({"strategy_id": strategy_id}, separators=(",", ":"), sort_keys=True)
    return f"opt-{hashlib.sha256(canonical.encode()).hexdigest()[:12]}"


def deterministic_executive_optimization_hash(opt: "ExecutiveOptimization") -> str:
    """Deterministic replay hash for a fully populated ``ExecutiveOptimization``.
    """
    data = {
        "id": opt.id,
        "strategy_id": opt.strategy_id,
        "optimization_score": opt.optimization_score,
        "confidence": opt.confidence,
        "supporting_profile_ids": list(opt.supporting_profile_ids),
        "supporting_bias_ids": list(opt.supporting_bias_ids),
        "recommendation": opt.recommendation,
        "first_seen_tick": opt.first_seen_tick,
        "last_seen_tick": opt.last_seen_tick,
    }
    json_repr = json.dumps(data, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(json_repr.encode()).hexdigest()


@dataclass(frozen=True)
class ExecutiveOptimization:
    """Immutable aggregation of adaptation and policy insights for a strategy.

    ``optimization_score`` – weighted combination of adaptation confidence and
    policy confidence.
    ``confidence`` – Laplace‑smoothed success probability derived from the
    adaptation profile successes/failures.
    ``recommendation`` – deterministic recommendation based on the score.
    """
    id: str
    strategy_id: str
    optimization_score: float
    confidence: float
    supporting_profile_ids: Tuple[str, ...]
    supporting_bias_ids: Tuple[str, ...]
    recommendation: str
    first_seen_tick: int
    last_seen_tick: int
    replay_hash: str

    @staticmethod
    def create(
        strategy_id: str,
        optimization_score: float,
        confidence: float,
        recommendation: str,
        supporting_profile_ids: Tuple[str, ...] = (),
        supporting_bias_ids: Tuple[str, ...] = (),
        first_seen_tick: int = 0,
        last_seen_tick: int = 0,
    ) -> "ExecutiveOptimization":
        """Factory that creates a deterministic ``ExecutiveOptimization``.
        """
        opt_id = deterministic_executive_optimization_id(strategy_id)
        placeholder = ExecutiveOptimization(
            id=opt_id,
            strategy_id=strategy_id,
            optimization_score=optimization_score,
            confidence=confidence,
            supporting_profile_ids=supporting_profile_ids,
            supporting_bias_ids=supporting_bias_ids,
            recommendation=recommendation,
            first_seen_tick=first_seen_tick,
            last_seen_tick=last_seen_tick,
            replay_hash="",
        )
        return replace(placeholder, replay_hash=deterministic_executive_optimization_hash(placeholder))
