"""Deterministic executive self‑improvement signal generation.

Creates ``ExecutiveImprovementSignal`` objects from the persisted
``ExecutiveOptimization`` records. All operations are pure cognition.
"""

from __future__ import annotations

from typing import List

from .executive_optimization import ExecutiveOptimization
from .executive_self_improvement import ExecutiveImprovementSignal


def generate_self_improvement_signals(
    optimization_store: "scrubin.cognition.executive_optimization_store.ExecutiveOptimizationStore",
) -> List[ExecutiveImprovementSignal]:
    """Generate deterministic self‑improvement signals for each optimization.

    The signal mirrors the underlying optimization's score, confidence, and
    recommendation, and records the optimization ID as supporting evidence.
    """
    signals: List[ExecutiveImprovementSignal] = []
    for opt in optimization_store.optimizations:
        signal = ExecutiveImprovementSignal.create(
            strategy_id=opt.strategy_id,
            optimization_score=opt.optimization_score,
            confidence=opt.confidence,
            recommendation=opt.recommendation,
            supporting_optimization_ids=(opt.id,),
        )
        signals.append(signal)
    return signals
