"""Deterministic policy refinement based on executive evaluations.

Generates advisory ``PolicyRecommendation`` objects that suggest actions for a
strategy based on aggregated evaluation scores.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from typing import Tuple, List, Dict

from .executive_evaluation import ExecutiveEvaluation
from .executive_evaluation_store import ExecutiveEvaluationStore
from .strategy import Strategy
from .strategy_store import StrategyStore


def deterministic_policy_id(strategy_id: str, recommendation: str) -> str:
    """Deterministic identifier for a policy recommendation.

    ``recommendation`` is a short string such as ``"continue"``.
    """
    canonical = json.dumps({"strategy_id": strategy_id, "recommendation": recommendation}, separators=(",", ":"), sort_keys=True)
    return f"policy-{hashlib.sha256(canonical.encode()).hexdigest()[:12]}"


def deterministic_policy_hash(policy: "PolicyRecommendation") -> str:
    """Deterministic replay hash for a ``PolicyRecommendation``.
    """
    data = {
        "id": policy.id,
        "strategy_id": policy.strategy_id,
        "recommendation": policy.recommendation,
        "supporting_evaluation_ids": list(policy.supporting_evaluation_ids),
        "confidence": policy.confidence,
    }
    json_repr = json.dumps(data, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(json_repr.encode()).hexdigest()


@dataclass(frozen=True)
class PolicyRecommendation:
    id: str
    strategy_id: str
    recommendation: str
    supporting_evaluation_ids: Tuple[str, ...]
    confidence: float
    replay_hash: str

    @staticmethod
    def create(
        strategy_id: str,
        recommendation: str,
        supporting_evaluation_ids: Tuple[str, ...] = (),
        confidence: float = 0.0,
    ) -> "PolicyRecommendation":
        policy_id = deterministic_policy_id(strategy_id, recommendation)
        placeholder = PolicyRecommendation(
            id=policy_id,
            strategy_id=strategy_id,
            recommendation=recommendation,
            supporting_evaluation_ids=supporting_evaluation_ids,
            confidence=confidence,
            replay_hash="",
        )
        return replace(placeholder, replay_hash=deterministic_policy_hash(placeholder))


def run_policy_refinement(evaluation_store: ExecutiveEvaluationStore, strategy_store: StrategyStore) -> List[PolicyRecommendation]:
    """Determine deterministic policy recommendations for each strategy.

    The average evaluation score per strategy drives the recommendation:
        ≥ 0.75 → ``continue``
        ≥ 0.50 → ``strengthen``
        ≥ 0.25 → ``weaken``
        else   → ``retire``
    ``confidence`` mirrors the average evaluation score.
    """
    # Aggregate evaluations per strategy
    evals_by_strategy: Dict[str, List[ExecutiveEvaluation]] = {}
    for ev in evaluation_store.evaluations:
        evals_by_strategy.setdefault(ev.strategy_id, []).append(ev)

    recommendations: List[PolicyRecommendation] = []
    for strategy in strategy_store.strategies:
        evs = evals_by_strategy.get(strategy.id, [])
        if evs:
            avg_score = sum(ev.evaluation_score for ev in evs) / len(evs)
        else:
            avg_score = 0.0
        if avg_score >= 0.75:
            rec = "continue"
        elif avg_score >= 0.50:
            rec = "strengthen"
        elif avg_score >= 0.25:
            rec = "weaken"
        else:
            rec = "retire"
        recommendation = PolicyRecommendation.create(
            strategy_id=strategy.id,
            recommendation=rec,
            supporting_evaluation_ids=tuple(ev.id for ev in evs),
            confidence=avg_score,
        )
        recommendations.append(recommendation)
    return recommendations
