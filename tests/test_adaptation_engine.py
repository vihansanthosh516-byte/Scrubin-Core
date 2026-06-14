"""Tests for deterministic adaptation profile aggregation and bias generation.

Covers ID determinism, merging, confidence calculation, bias computation, and replay
safety across multiple updates.
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
from scrubin.cognition.executive_feedback_store import ExecutiveFeedbackStore
from scrubin.cognition.executive_feedback_engine import update_executive_feedback
from scrubin.cognition.adaptation_store import AdaptationStore
from scrubin.cognition.adaptation_engine import update_adaptation_profiles
from scrubin.cognition.adaptation_bias_engine import generate_adaptation_biases
from scrubin.cognition.adaptation_bias import AdaptationBias


def test_adaptation_profile_aggregation_and_bias():
    # ----- Setup deterministic strategy -----
    strategy = Strategy.create(
        name="adapt-test-strategy",
        description="Strategy for adaptation testing",
        trigger_conditions=(),
        action_sequence=("a1", "a2"),
        confidence=0.75,
        success_count=0,
        failure_count=0,
        supporting_plan_ids=(),
        first_seen_tick=0,
        last_seen_tick=0,
    )
    strat_store = StrategyStore()
    strat_store.add_or_update(strategy)

    # ----- Executive goal and selection -----
    goal = ExecutiveGoal.create(
        description="adapt‑goal",
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

    # ----- First executive evaluation -----
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

    # ----- Policy profile and bias -----
    policy_store = PolicyStore()
    update_policy_profiles(eval_store, strat_store, sel_store, policy_store)
    biases = generate_strategy_bias(policy_store)
    assert len(biases) == 1
    # ----- Bias plan candidate -----
    bias_plan_store = BiasPlanStore()
    update_bias_plan_candidates(
        executive_store=None,
        strategy_store=strat_store,
        selection_store=sel_store,
        policy_store=policy_store,
        strategy_biases=biases,
        plan_store=bias_plan_store,
    )
    assert bias_plan_store.candidate_count() == 1

    # ----- Executive feedback -----
    feedback_store = ExecutiveFeedbackStore()
    update_executive_feedback(eval_store, policy_store, bias_plan_store, feedback_store)
    assert feedback_store.feedback_count() == 1
    fb = feedback_store.feedbacks[0]
    # ----- Adaptation profile generation -----
    adaptation_store = AdaptationStore()
    update_adaptation_profiles(feedback_store, policy_store, adaptation_store)
    assert adaptation_store.profile_count() == 1
    profile = adaptation_store.profiles[0]
    # Verify deterministic ID (based on strategy)
    from scrubin.cognition.adaptation_profile import deterministic_adaptation_profile_id
    expected_id = deterministic_adaptation_profile_id(strategy.id)
    assert profile.id == expected_id
    # Executions and success/failure counts
    assert profile.executions == 1
    assert profile.successful_adaptations == 1 if fb.confidence_delta > 0 else 0
    assert profile.failed_adaptations == 0 if fb.confidence_delta > 0 else 1
    # Average delta matches feedback delta
    assert math.isclose(profile.average_delta, fb.confidence_delta, rel_tol=1e-9)
    # Confidence = (success+1)/(success+failure+2)
    exp_conf = (profile.successful_adaptations + 1) / (profile.successful_adaptations + profile.failed_adaptations + 2)
    assert math.isclose(profile.confidence, exp_conf, rel_tol=1e-9)
    # Supporting IDs contain the feedback and policy IDs
    assert profile.supporting_feedback_ids == (fb.id,)
    # ----- Add a second feedback with negative delta -----
    eval2 = ExecutiveEvaluation.create(
        goal_id=goal.id,
        strategy_id=strategy.id,
        selection_id=selection.id,
        evaluation_score=0.4,
        outcome_score=0.0,
        confidence_score=0.5,
        supporting_episode_ids=(),
        supporting_fact_ids=(),
        supporting_belief_ids=(),
        supporting_reflection_ids=(),
        supporting_counterfactual_ids=(),
        tick=2,
    )
    eval_store.add_or_update(eval2)
    # Re‑run feedback and adaptation updates – should merge into existing profile
    update_executive_feedback(eval_store, policy_store, bias_plan_store, feedback_store)
    update_adaptation_profiles(feedback_store, policy_store, adaptation_store)
    assert adaptation_store.profile_count() == 1
    merged = adaptation_store.profiles[0]
    assert merged.executions == 2
    # Determine expected success/failure counts
    expected_success = 1 if fb.confidence_delta > 0 else 0
    # For second feedback, compute its delta
    # Retrieve latest feedback for second evaluation
    latest_fb = feedback_store.feedbacks[-1]
    second_success = 1 if latest_fb.confidence_delta > 0 else 0
    expected_success += second_success
    expected_failure = 2 - expected_success
    assert merged.successful_adaptations == expected_success
    assert merged.failed_adaptations == expected_failure
    # Weighted average delta
    total_delta = fb.confidence_delta + latest_fb.confidence_delta
    expected_avg = total_delta / 2
    assert math.isclose(merged.average_delta, expected_avg, rel_tol=1e-9)
    # ----- Adaptation bias generation -----
    biases = generate_adaptation_biases(adaptation_store)
    assert len(biases) == 1
    ab = biases[0]
    # Bias should be average_delta * confidence
    expected_bias = merged.average_delta * merged.confidence
    assert math.isclose(ab.bias, expected_bias, rel_tol=1e-9)
    assert ab.strategy_id == strategy.id
