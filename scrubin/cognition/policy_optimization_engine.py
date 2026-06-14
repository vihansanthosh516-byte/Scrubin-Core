"""Deterministic policy optimization engine.

Aggregates ``ExecutiveEvaluation`` objects per strategy into ``PolicyProfile`` entries.
All calculations are deterministic and produce immutable ``PolicyProfile``
instances that are stored in an append‑only ``PolicyStore``.
"""

from __future__ import annotations

from typing import Tuple

from .executive_evaluation import ExecutiveEvaluation
from .executive_evaluation_store import ExecutiveEvaluationStore
from .strategy import Strategy
from .strategy_store import StrategyStore
from .strategy_selection_store import StrategySelectionStore
from .policy_profile import PolicyProfile
from .policy_store import PolicyStore


def _determine_recommendation(avg_score: float) -> str:
    """Map average evaluation score to a recommendation string.

    Mirrors the thresholds used in ``policy_refinement`` for consistency.
    """
    if avg_score >= 0.75:
        return "continue"
    elif avg_score >= 0.50:
        return "strengthen"
    elif avg_score >= 0.25:
        return "weaken"
    else:
        return "retire"


def update_policy_profiles(
    evaluation_store: ExecutiveEvaluationStore,
    strategy_store: StrategyStore,
    selection_store: StrategySelectionStore,
    policy_store: PolicyStore,
) -> None:
    """Update ``PolicyStore`` with aggregated profiles for each strategy.

    For each strategy present in ``strategy_store`` we collect all associated
    ``ExecutiveEvaluation`` objects, compute deterministic aggregates, and add or
    update the corresponding ``PolicyProfile`` in ``policy_store``.
    """
    # Group evaluations by strategy ID
    evals_by_strategy: dict[str, list[ExecutiveEvaluation]] = {}
    for ev in evaluation_store.evaluations:
        evals_by_strategy.setdefault(ev.strategy_id, []).append(ev)

    for strategy in strategy_store.strategies:
        # Gather all evaluations for this strategy
        all_evs = evals_by_strategy.get(strategy.id, [])
        # Determine the last processed tick for this strategy (if a profile exists)
        prior_profiles = policy_store.query(strategy_id=strategy.id)
        last_processed_tick = 0
        if prior_profiles:
            # Since store preserves insertion order, the latest profile is the last entry
            last_processed_tick = prior_profiles[-1].last_seen_tick
        # New evaluations are those with tick > last_processed_tick
        evs = [ev for ev in all_evs if ev.tick > last_processed_tick]
        executions = len(evs)
        if executions == 0:
            # No new data – skip creating a profile for this tick
            continue
        success_count = sum(1 for ev in evs if ev.outcome_score >= 0.5)
        failure_count = executions - success_count
        average_score = sum(ev.evaluation_score for ev in evs) / executions if executions else 0.0
        confidence = (success_count + 1) / (success_count + failure_count + 2) if (success_count + failure_count + 2) > 0 else 0.0
        recommendation = _determine_recommendation(average_score)
        recommendation_history = (recommendation,)
        supporting_ids = tuple(sorted(ev.id for ev in evs))
        first_tick = min((ev.tick for ev in evs), default=0)
        last_tick = max((ev.tick for ev in evs), default=0)
        profile = PolicyProfile.create(
            strategy_id=strategy.id,
            executions=executions,
            success_count=success_count,
            failure_count=failure_count,
            average_score=average_score,
            confidence=confidence,
            recommendation_history=recommendation_history,
            supporting_evaluation_ids=supporting_ids,
            first_seen_tick=first_tick,
            last_seen_tick=last_tick,
        )
        policy_store.add_or_update(profile)
