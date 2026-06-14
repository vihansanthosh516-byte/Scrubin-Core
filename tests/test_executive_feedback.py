"""Tests for deterministic executive feedback and adaptation signals.

Covers ID/replay hash determinism, error calculations, merge behavior, and
signal generation.
"""

from __future__ import annotations

import math

from scrubin.cognition.strategy import Strategy
from scrubin.cognition.strategy_store import StrategyStore
from scrubin.cognition.executive_goal import ExecutiveGoal
from scrubin.cognition.strategy_selection import StrategySelection
from scrubin.cognition.strategy_selection_store import StrategySelectionStore
from scrubin.cognition.executive_evaluation import ExecutiveEvaluation
from scrubin.cognition.executive_evaluation_store import ExecutiveEvaluationStore
from scrubin.cognition.policy_store import PolicyStore
from scrubin.cognition.policy_optimization_engine import update_policy_profiles
from scrubin.cognition.strategy_bias_engine import generate_strategy_bias
from scrubin.cognition.bias_plan_store import BiasPlanStore
from scrubin.cognition.bias_planner_engine import update_bias_plan_candidates
from scrubin.cognition.executive_feedback import (
    ExecutiveFeedback,
    deterministic_executive_feedback_id,
)
from scrubin.cognition.executive_feedback_store import ExecutiveFeedbackStore
from scrubin.cognition.executive_feedback_engine import update_executive_feedback
from scrubin.cognition.executive_adaptation import generate_adaptation_signals, AdaptationSignal


def test_executive_feedback_and_adaptation():
    # ---- Setup deterministic strategy ----
    strategy = Strategy.create(
        name="fb-test-strategy",
        description="Strategy for feedback testing",
        trigger_conditions=(),
        action_sequence=("a1", "a2"),
        confidence=0.7,
        success_count=0,
        failure_count=0,
        supporting_plan_ids=(),
        first_seen_tick=0,
        last_seen_tick=0,
    )
    strat_store = StrategyStore()
    strat_store.add_or_update(strategy)

    # ---- Executive goal and selection ----
    goal = ExecutiveGoal.create(
        description="test‑goal",
        priority=1.0,
        confidence=1.0,
        status="pending",
        supporting_patterns=(),
        supporting_beliefs=(),
        created_tick=1,
    )
    selection = StrategySelection.create(
        goal_id=goal.id,
        strategy_id=strategy.id,
        score=strategy.confidence,
        selection_reason="test",
        supporting_strategy_ids=(strategy.id,),
        supporting_belief_ids=(),
        supporting_reflection_ids=(),
        tick=1,
    )
    sel_store = StrategySelectionStore()
    sel_store.add_or_update(selection)

    # ---- Executive evaluation (first tick) ----
    eval_store = ExecutiveEvaluationStore()
    eval1 = ExecutiveEvaluation.create(
        goal_id=goal.id,
        strategy_id=strategy.id,
        selection_id=selection.id,
        evaluation_score=0.9,
        outcome_score=1.0,
        confidence_score=0.95,
        supporting_episode_ids=(),
        supporting_fact_ids=(),
        supporting_belief_ids=(),
        supporting_reflection_ids=(),
        supporting_counterfactual_ids=(),
        tick=1,
    )
    eval_store.add_or_update(eval1)

    # ---- Policy profile & bias ----
    policy_store = PolicyStore()
    update_policy_profiles(eval_store, strat_store, sel_store, policy_store)
    assert policy_store.profile_count() == 1
    profile = policy_store.profiles[0]
    biases = generate_strategy_bias(policy_store)
    assert len(biases) == 1
    bias = biases[0]

    # ---- Bias plan candidate ----
    bias_plan_store = BiasPlanStore()
    update_bias_plan_candidates(
        executive_store=None,  # Not used in current implementation
        strategy_store=strat_store,
        selection_store=sel_store,
        policy_store=policy_store,
        strategy_biases=biases,
        plan_store=bias_plan_store,
    )
    assert bias_plan_store.candidate_count() == 1
    candidate = bias_plan_store.candidates[0]

    # ---- Executive feedback generation ----
    feedback_store = ExecutiveFeedbackStore()
    update_executive_feedback(eval_store, policy_store, bias_plan_store, feedback_store)
    assert feedback_store.feedback_count() == 1
    fb = feedback_store.feedbacks[0]
    # Deterministic ID check
    expected_id = deterministic_executive_feedback_id(goal.id, strategy.id)
    assert fb.id == expected_id
    # Prediction error = |policy_confidence - evaluation_score|
    expected_error = abs(profile.confidence - eval1.evaluation_score)
    assert math.isclose(fb.prediction_error, expected_error, rel_tol=1e-9)
    # Confidence delta = evaluation_score - policy_confidence
    expected_delta = eval1.evaluation_score - profile.confidence
    assert math.isclose(fb.confidence_delta, expected_delta, rel_tol=1e-9)
    # Bias used matches candidate bias_score
    assert math.isclose(fb.bias_used, candidate.bias_score, rel_tol=1e-9)
    # Supporting IDs
    assert fb.supporting_policy_ids == (profile.id,)
    assert fb.supporting_evaluation_ids == (eval1.id,)

    # ---- Add a second evaluation with lower score ----
    eval2 = ExecutiveEvaluation.create(
        goal_id=goal.id,
        strategy_id=strategy.id,
        selection_id=selection.id,
        evaluation_score=0.5,
        outcome_score=0.0,
        confidence_score=0.6,
        supporting_episode_ids=(),
        supporting_fact_ids=(),
        supporting_belief_ids=(),
        supporting_reflection_ids=(),
        supporting_counterfactual_ids=(),
        tick=2,
    )
    eval_store.add_or_update(eval2)
    # Re‑run feedback update – should merge with prior feedback (same ID)
    update_executive_feedback(eval_store, policy_store, bias_plan_store, feedback_store)
    # Still only one feedback entry (merged)
    assert feedback_store.feedback_count() == 1
    merged_fb = feedback_store.feedbacks[0]
    # Evaluation score should be the max of the two evaluations (0.9)
    assert merged_fb.evaluation_score == max(eval1.evaluation_score, eval2.evaluation_score)
    # Tick should be the later tick (2)
    assert merged_fb.tick == 2
    # Supporting IDs should include both evaluations
    assert set(merged_fb.supporting_evaluation_ids) == {eval1.id, eval2.id}
    # Prediction error reflects the same policy confidence (unchanged) vs max eval
    expected_error2 = abs(profile.confidence - merged_fb.evaluation_score)
    assert math.isclose(merged_fb.prediction_error, expected_error2, rel_tol=1e-9)

    # ---- Adaptation signal generation ----
    signals = generate_adaptation_signals(feedback_store)
    # One signal for the strategy
    assert len(signals) == 1
    sig = signals[0]
    assert sig.strategy_id == strategy.id
    # Adjustment = mean confidence_delta across feedback (only one merged entry)
    expected_adjustment = merged_fb.confidence_delta
    assert math.isclose(sig.adjustment, expected_adjustment, rel_tol=1e-9)
    # Confidence = (positive_count+1)/(total+2); positive count is 1 if delta>0 else 0
    positive = 1 if merged_fb.confidence_delta > 0 else 0
    expected_confidence = (positive + 1) / (1 + 2)
    assert math.isclose(sig.confidence, expected_confidence, rel_tol=1e-9)
