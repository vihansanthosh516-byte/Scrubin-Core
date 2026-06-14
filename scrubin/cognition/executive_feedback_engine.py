"""Deterministic executive feedback engine.

Creates ``ExecutiveFeedback`` records that compare the policy confidence and bias
used during planning with the actual evaluation outcome.
All operations are pure cognition; no world mutation occurs.
"""

from __future__ import annotations

from typing import Tuple

from .executive_feedback import ExecutiveFeedback
from .executive_feedback_store import ExecutiveFeedbackStore
from .executive_evaluation import ExecutiveEvaluation
from .executive_evaluation_store import ExecutiveEvaluationStore
from .policy_store import PolicyStore
from .bias_plan_store import BiasPlanStore


def update_executive_feedback(
    evaluation_store: ExecutiveEvaluationStore,
    policy_store: PolicyStore,
    bias_plan_store: BiasPlanStore,
    feedback_store: ExecutiveFeedbackStore,
) -> None:
    """Generate deterministic feedback records for each executive evaluation.

    For every ``ExecutiveEvaluation`` we locate the corresponding ``PolicyProfile``
    (by strategy) and ``BiasPlanCandidate`` (by goal and strategy). The feedback
    captures the prediction error and confidence delta, as well as the raw
    policy confidence and bias used.
    """
    # Build lookup maps for quick access
    # Policy profiles are indexed by strategy_id – pick the latest profile per strategy
    policy_by_strategy: dict[str, "scrubin.cognition.policy_profile.PolicyProfile"] = {}
    for profile in policy_store.profiles:
        # Since insertion order is deterministic, later profiles overwrite earlier ones
        policy_by_strategy[profile.strategy_id] = profile

    # Bias candidates indexed by (goal_id, strategy_id) – pick latest per pair
    bias_by_pair: dict[Tuple[str, str], "scrubin.cognition.bias_plan_candidate.BiasPlanCandidate"] = {}
    for cand in bias_plan_store.candidates:
        bias_by_pair[(cand.goal_id, cand.strategy_id)] = cand

    for ev in evaluation_store.evaluations:
        # Locate supporting policy profile
        profile = policy_by_strategy.get(ev.strategy_id)
        policy_conf = profile.confidence if profile is not None else 0.0
        supporting_policy_ids = (profile.id,) if profile is not None else ()
        # Locate bias candidate
        bias_cand = bias_by_pair.get((ev.goal_id, ev.strategy_id))
        bias_used = bias_cand.bias_score if bias_cand is not None else 0.0
        # Compute prediction error and confidence delta
        prediction_error = abs(policy_conf - ev.evaluation_score)
        confidence_delta = ev.evaluation_score - policy_conf
        # Create feedback entry
        feedback = ExecutiveFeedback.create(
            goal_id=ev.goal_id,
            strategy_id=ev.strategy_id,
            evaluation_score=ev.evaluation_score,
            policy_confidence=policy_conf,
            bias_used=bias_used,
            prediction_error=prediction_error,
            confidence_delta=confidence_delta,
            tick=ev.tick,
            supporting_policy_ids=supporting_policy_ids,
            supporting_evaluation_ids=(ev.id,),
        )
        feedback_store.add_or_update(feedback)
