"""Deterministic adaptation engine.

Aggregates ``ExecutiveFeedback`` entries into ``AdaptationProfile`` records per strategy.
All operations are pure cognition – no world mutation.
"""

from __future__ import annotations

from typing import Tuple, Dict

from .executive_feedback import ExecutiveFeedback
from .executive_feedback_store import ExecutiveFeedbackStore
from .policy_store import PolicyStore
from .adaptation_profile import AdaptationProfile
from .adaptation_store import AdaptationStore


def update_adaptation_profiles(
    feedback_store: ExecutiveFeedbackStore,
    policy_store: PolicyStore,
    adaptation_store: AdaptationStore,
) -> None:
    """Create or merge ``AdaptationProfile`` objects from feedback.

    For each strategy we collect all feedback entries (including prior ones) and
    compute aggregated statistics. The store's ``add_or_update`` method merges
    duplicate profiles deterministically.
    """
    # Group feedback by strategy ID
    feedback_by_strategy: Dict[str, list[ExecutiveFeedback]] = {}
    for fb in feedback_store.feedbacks:
        feedback_by_strategy.setdefault(fb.strategy_id, []).append(fb)

    # Build map of policy confidence per strategy for possible future use (not needed here)
    _ = {p.strategy_id: p.confidence for p in policy_store.profiles}

    for strategy_id, fbs in feedback_by_strategy.items():
        executions = len(fbs)
        successes = sum(1 for fb in fbs if fb.confidence_delta > 0)
        failures = executions - successes
        avg_delta = sum(fb.confidence_delta for fb in fbs) / executions if executions else 0.0
        conf = (successes + 1) / (successes + failures + 2) if (successes + failures + 2) > 0 else 0.0
        supporting_feedback_ids = tuple(sorted(fb.id for fb in fbs))
        supporting_policy_ids = tuple(sorted({pid for fb in fbs for pid in fb.supporting_policy_ids}))
        first_tick = min(fb.tick for fb in fbs)
        last_tick = max(fb.tick for fb in fbs)
        profile = AdaptationProfile.create(
            strategy_id=strategy_id,
            executions=executions,
            successful_adaptations=successes,
            failed_adaptations=failures,
            average_delta=avg_delta,
            confidence=conf,
            supporting_feedback_ids=supporting_feedback_ids,
            supporting_policy_ids=supporting_policy_ids,
            first_seen_tick=first_tick,
            last_seen_tick=last_tick,
        )
        adaptation_store.add_or_update(profile)
