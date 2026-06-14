"""Immutable deterministic executive self‑improvement signal model.

Signals are derived from ``ExecutiveOptimization`` entries and guide future
planning by biasing strategies toward those with strong optimization scores.
All fields are frozen; updates use ``replace``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from typing import Tuple


def deterministic_self_improvement_signal_id(strategy_id: str) -> str:
    """Deterministic identifier for an ``ExecutiveImprovementSignal``.

    The ID is ``selfimp-`` plus the first 12 hex characters of a SHA‑256 hash
    over a canonical JSON representation of the ``strategy_id``.
    """
    canonical = json.dumps({"strategy_id": strategy_id}, separators=(",", ":"), sort_keys=True)
    return f"selfimp-{hashlib.sha256(canonical.encode()).hexdigest()[:12]}"


def deterministic_self_improvement_signal_hash(sig: "ExecutiveImprovementSignal") -> str:
    """Deterministic replay hash for a fully populated ``ExecutiveImprovementSignal``.
    """
    data = {
        "id": sig.id,
        "strategy_id": sig.strategy_id,
        "optimization_score": sig.optimization_score,
        "confidence": sig.confidence,
        "recommendation": sig.recommendation,
        "supporting_optimization_ids": list(sig.supporting_optimization_ids),
    }
    json_repr = json.dumps(data, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(json_repr.encode()).hexdigest()


@dataclass(frozen=True)
class ExecutiveImprovementSignal:
    """Immutable signal recommending a planning adjustment for a strategy.

    ``optimization_score`` – the weighted score from ``ExecutiveOptimization``.
    ``confidence`` – same confidence as the underlying optimization.
    ``recommendation`` – deterministic recommendation string.
    """
    id: str
    strategy_id: str
    optimization_score: float
    confidence: float
    recommendation: str
    supporting_optimization_ids: Tuple[str, ...]
    replay_hash: str

    @staticmethod
    def create(
        strategy_id: str,
        optimization_score: float,
        confidence: float,
        recommendation: str,
        supporting_optimization_ids: Tuple[str, ...] = (),
    ) -> "ExecutiveImprovementSignal":
        sig_id = deterministic_self_improvement_signal_id(strategy_id)
        placeholder = ExecutiveImprovementSignal(
            id=sig_id,
            strategy_id=strategy_id,
            optimization_score=optimization_score,
            confidence=confidence,
            recommendation=recommendation,
            supporting_optimization_ids=supporting_optimization_ids,
            replay_hash="",
        )
        return replace(placeholder, replay_hash=deterministic_self_improvement_signal_hash(placeholder))
