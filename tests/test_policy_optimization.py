"""Tests for deterministic policy optimization and bias generation.

Ensures that policy profiles are created, merged, and queried deterministically,
and that strategy bias objects are derived correctly from profiles.
"""

from __future__ import annotations

import math

from scrubin.cognition.strategy import Strategy
from scrubin.cognition.policy_store import PolicyStore
from scrubin.cognition.executive_evaluation import ExecutiveEvaluation
from scrubin.cognition.executive_evaluation_store import ExecutiveEvaluationStore
from scrubin.cognition.strategy_selection_store import StrategySelectionStore
from scrubin.cognition.policy_optimization_engine import update_policy_profiles
from scrubin.cognition.policy_profile import deterministic_policy_profile_id
from scrubin.cognition.strategy_bias_engine import generate_strategy_bias


def test_policy_profile_aggregation_and_merging():
    # Set up a deterministic strategy
    strategy = Strategy.create(
        name="test-strategy",
        description="A test strategy",
        trigger_conditions=(),
        action_sequence=("action1", "action2"),
        success_count=0,
        failure_count=0,
        confidence=0.0,
        supporting_plan_ids=(),
        first_seen_tick=0,
        last_seen_tick=0,
    )
    # Store the strategy (needed for lookup)
    from scrubin.cognition.strategy_store import StrategyStore

    strategy_store = StrategyStore()
    strategy_store.add_or_update(strategy)

    # Create executive evaluation store and add first evaluation (tick=1, success)
    eval_store = ExecutiveEvaluationStore()
    ev1 = ExecutiveEvaluation.create(
        goal_id="goal-1",
        strategy_id=strategy.id,
        selection_id="sel-1",
        evaluation_score=0.8,
        outcome_score=1.0,
        confidence_score=0.9,
        supporting_episode_ids=(),
        supporting_fact_ids=(),
        supporting_belief_ids=(),
        supporting_reflection_ids=(),
        supporting_counterfactual_ids=(),
        tick=1,
    )
    eval_store.add_or_update(ev1)

    # Empty selection store (not used by the engine)
    selection_store = StrategySelectionStore()

    # Create policy store and run optimization for the first tick
    policy_store = PolicyStore()
    update_policy_profiles(eval_store, strategy_store, selection_store, policy_store)

    # Verify a single profile exists with correct aggregated values
    assert policy_store.profile_count() == 1
    profile = policy_store.profiles[0]
    # Deterministic ID based on strategy ID
    expected_id = deterministic_policy_profile_id(strategy.id)
    assert profile.id == expected_id
    # Executions and success/failure counts
    assert profile.executions == 1
    assert profile.success_count == 1
    assert profile.failure_count == 0
    # Average score and confidence
    assert math.isclose(profile.average_score, 0.8, rel_tol=1e-9)
    # Confidence formula: (success+1)/(success+failure+2) = (1+1)/(1+0+2) = 2/3
    assert math.isclose(profile.confidence, 2 / 3, rel_tol=1e-9)
    # Recommendation based on average score >=0.75 -> continue
    assert profile.recommendation_history == ("continue",)
    # Supporting evaluation IDs contain the first evaluation
    assert profile.supporting_evaluation_ids == (ev1.id,)
    # Ticks correctly recorded
    assert profile.first_seen_tick == 1
    assert profile.last_seen_tick == 1

    # Add second evaluation (tick=2, failure)
    ev2 = ExecutiveEvaluation.create(
        goal_id="goal-1",
        strategy_id=strategy.id,
        selection_id="sel-1",
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
    eval_store.add_or_update(ev2)

    # Run optimization again – should merge new data
    update_policy_profiles(eval_store, strategy_store, selection_store, policy_store)

    # After merging, profile should reflect both evaluations
    assert policy_store.profile_count() == 1
    merged = policy_store.profiles[0]
    assert merged.executions == 2
    assert merged.success_count == 1
    assert merged.failure_count == 1
    # Weighted average: (0.8 + 0.4) / 2 = 0.6
    assert math.isclose(merged.average_score, 0.6, rel_tol=1e-9)
    # Confidence: (1+1)/(1+1+2) = 2/4 = 0.5
    assert math.isclose(merged.confidence, 0.5, rel_tol=1e-9)
    # Recommendation history should contain both recommendations (sorted)
    # ev2 avg_score 0.4 -> "weaken"
    assert merged.recommendation_history == ("continue", "weaken")
    # Supporting IDs contain both evaluations (sorted)
    assert merged.supporting_evaluation_ids == tuple(sorted([ev1.id, ev2.id]))
    # Tick range updated
    assert merged.first_seen_tick == 1
    assert merged.last_seen_tick == 2


def test_strategy_bias_generation():
    # Reuse the setup from the previous test to obtain a populated policy store
    strategy = Strategy.create(
        name="bias-strategy",
        description="Strategy for bias test",
        trigger_conditions=(),
        action_sequence=("act"),
        success_count=0,
        failure_count=0,
        confidence=0.0,
        supporting_plan_ids=(),
        first_seen_tick=0,
        last_seen_tick=0,
    )
    from scrubin.cognition.strategy_store import StrategyStore

    strategy_store = StrategyStore()
    strategy_store.add_or_update(strategy)

    eval_store = ExecutiveEvaluationStore()
    ev = ExecutiveEvaluation.create(
        goal_id="goal-bias",
        strategy_id=strategy.id,
        selection_id="sel-bias",
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
    eval_store.add_or_update(ev)
    selection_store = StrategySelectionStore()
    policy_store = PolicyStore()
    update_policy_profiles(eval_store, strategy_store, selection_store, policy_store)

    # Generate bias objects
    biases = generate_strategy_bias(policy_store)
    assert len(biases) == 1
    bias = biases[0]
    # Bias should reflect the profile's confidence after aggregation (single eval confidence = 2/3)
    expected_confidence = (1 + 1) / (1 + 0 + 2)  # success=1, failure=0
    assert math.isclose(bias.bias, expected_confidence, rel_tol=1e-9)
    # Supporting policy IDs should include the single profile ID
    assert bias.supporting_policy_ids == (policy_store.profiles[0].id,)
    assert bias.strategy_id == strategy.id
