"""Deterministic executive adaptation signal generation.

Based on accumulated ``ExecutiveFeedback`` records, this module produces
``AdaptationSignal`` objects that quantify how a strategy's planning confidence
should be adjusted.
All objects are immutable and deterministically identified.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from typing import Tuple, List, Dict

from .executive_feedback_store import ExecutiveFeedbackStore


def deterministic_adaptation_signal_hash(signal: "AdaptationSignal") -> str:
    """Deterministic replay hash for a fully populated ``AdaptationSignal``.
    """
    data = {
        "strategy_id": signal.strategy_id,
        "adjustment": signal.adjustment,
        "confidence": signal.confidence,
    }
    json_repr = json.dumps(data, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(json_repr.encode()).hexdigest()


@dataclass(frozen=True)
class AdaptationSignal:
    """Immutable signal recommending adaptation for a strategy.

    ``adjustment`` – mean confidence delta across feedback (may be positive or negative).
    ``confidence`` – Laplace‑smoothed success probability based on positive vs total feedback.
    """
    strategy_id: str
    adjustment: float
    confidence: float
    replay_hash: str

    @staticmethod
    def create(
        strategy_id: str,
        adjustment: float,
        confidence: float,
    ) -> "AdaptationSignal":
        placeholder = AdaptationSignal(
            strategy_id=strategy_id,
            adjustment=adjustment,
            confidence=confidence,
            replay_hash="",
        )
        return replace(placeholder, replay_hash=deterministic_adaptation_signal_hash(placeholder))


def generate_adaptation_signals(
    feedback_store: ExecutiveFeedbackStore,
) -> List[AdaptationSignal]:
    """Generate deterministic adaptation signals from feedback records.

    For each strategy, ``adjustment`` is the mean ``confidence_delta`` across all
    related ``ExecutiveFeedback`` entries. ``confidence`` is computed as a Laplace‑
    smoothed success rate where a "success" is a positive ``confidence_delta``.
    """
    # Group feedback by strategy
    by_strategy: Dict[str, List[float]] = {}
    success_counts: Dict[str, int] = {}
    for fb in feedback_store.feedbacks:
        by_strategy.setdefault(fb.strategy_id, []).append(fb.confidence_delta)
        if fb.confidence_delta > 0:
            success_counts[fb.strategy_id] = success_counts.get(fb.strategy_id, 0) + 1
    signals: List[AdaptationSignal] = []
    for strategy_id, deltas in by_strategy.items():
        total = len(deltas)
        adjustment = sum(deltas) / total if total else 0.0
        successes = success_counts.get(strategy_id, 0)
        # Laplace smoothing: (success + 1) / (total + 2)
        confidence = (successes + 1) / (total + 2) if (total + 2) > 0 else 0.0
        signals.append(AdaptationSignal.create(strategy_id, adjustment, confidence))
    return signals
