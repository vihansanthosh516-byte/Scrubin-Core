"""Deterministic executive optimization engine.

Aggregates adaptation confidence and policy confidence into a persistent
optimization record for each strategy.
All calculations are deterministic and produce immutable ``ExecutiveOptimization``
objects stored in an ``ExecutiveOptimizationStore``.
"""

from __future__ import annotations

from typing import Dict, List

from .executive_optimization import ExecutiveOptimization
from .executive_optimization_store import ExecutiveOptimizationStore
from .adaptation_profile import AdaptationProfile
from .policy_profile import PolicyProfile


def _determine_recommendation(score: float) -> str:
    """Map optimization score to a deterministic recommendation.

    Thresholds (inclusive):
        >= 0.85 -> "strengthen"
        >= 0.70 -> "continue"
        >= 0.45 -> "monitor"
        else   -> "retire"
    """
    if score >= 0.85:
        return "strengthen"
    elif score >= 0.70:
        return "continue"
    elif score >= 0.45:
        return "monitor"
    else:
        return "retire"


def update_executive_optimizations(
    adaptation_store: "scrubin.cognition.adaptation_store.AdaptationStore",
    policy_store: "scrubin.cognition.policy_store.PolicyStore",
    optimization_store: ExecutiveOptimizationStore,
) -> None:
    """Create or update ``ExecutiveOptimization`` entries for each strategy.

    For each strategy we combine:
        * adaptation confidence (from ``AdaptationProfile.confidence``)
        * policy confidence (from ``PolicyProfile.confidence``)
    The weighted ``optimization_score`` is ``0.6*adapt_conf + 0.4*policy_conf``.
    ``confidence`` for the optimization is derived from the adaptation profile's
    success/failure counts using Laplace smoothing:
        ``(successful_adaptations + 1) / (successful_adaptations + failed_adaptations + 2)``.
    If a strategy lacks an adaptation profile or policy profile, missing values
    default to ``0.0``.
    """
    # Build lookup maps
    adaptation_map: Dict[str, AdaptationProfile] = {ap.strategy_id: ap for ap in adaptation_store.profiles}
    policy_map: Dict[str, PolicyProfile] = {p.strategy_id: p for p in policy_store.profiles}

    # Union of all strategy IDs present in either map
    strategy_ids = set(adaptation_map.keys()) | set(policy_map.keys())

    for sid in strategy_ids:
        adapt = adaptation_map.get(sid)
        policy = policy_map.get(sid)
        adapt_conf = adapt.confidence if adapt is not None else 0.0
        policy_conf = policy.confidence if policy is not None else 0.0
        opt_score = 0.6 * adapt_conf + 0.4 * policy_conf
        recommendation = _determine_recommendation(opt_score)
        # Confidence derived from adaptation successes/failures (Laplace)
        if adapt is not None:
            success = adapt.successful_adaptations
            failure = adapt.failed_adaptations
            conf = (success + 1) / (success + failure + 2) if (success + failure + 2) > 0 else 0.0
            first_tick = adapt.first_seen_tick
            last_tick = adapt.last_seen_tick
            supporting_profile_ids = (adapt.id,)
        else:
            # No adaptation data – default confidence 0 and empty support
            conf = 0.0
            first_tick = 0
            last_tick = 0
            supporting_profile_ids = ()
        # Supporting bias IDs – not directly used here (leave empty)
        supporting_bias_ids: tuple = ()
        opt_obj = ExecutiveOptimization.create(
            strategy_id=sid,
            optimization_score=opt_score,
            confidence=conf,
            recommendation=recommendation,
            supporting_profile_ids=supporting_profile_ids,
            supporting_bias_ids=supporting_bias_ids,
            first_seen_tick=first_tick,
            last_seen_tick=last_tick,
        )
        optimization_store.add_or_update(opt_obj)
