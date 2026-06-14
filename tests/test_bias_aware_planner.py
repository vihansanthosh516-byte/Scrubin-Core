"""Tests for bias‑aware planning and executive ranking.

Ensure deterministic IDs, hashes, scoring, merging, and ranking.
"""

from __future__ import annotations

import math

from scrubin.cognition.strategy import Strategy
from scrubin.cognition.strategy_store import StrategyStore
from scrubin.cognition.executive_store import ExecutiveStore
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
from scrubin.cognition.executive_ranking import compute_executive_ranking
from scrubin.cognition.bias_plan_candidate import deterministic_bias_plan_candidate_id


def test_bias_plan_candidate_creation_and_ranking():
    # 1️⃣ Create a deterministic strategy with known confidence
    strategy = Strategy.create(
        name="bias-test-strategy",
        description="Test strategy for bias planning",
        trigger_conditions=(),
        action_sequence=("act1", "act2"),
        success_count=0,
        failure_count=0,
        confidence=0.8,  # base confidence
        supporting_plan_ids=(),
        first_seen_tick=0,
        last_seen_tick=0,
    )
    strategy_store = StrategyStore()
    strategy_store.add_or_update(strategy)

    # 2️⃣ Create an executive goal and a selection linking them
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
    selection_store = StrategySelectionStore()
    selection_store.add_or_update(selection)

    # 3️⃣ Executive evaluation (single tick) – needed to generate a policy profile
    exec_eval_store = ExecutiveEvaluationStore()
    eval_obj = ExecutiveEvaluation.create(
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
    exec_eval_store.add_or_update(eval_obj)

    # 4️⃣ Policy profile generation (phase 4.4)
    policy_store = PolicyStore()
    update_policy_profiles(exec_eval_store, strategy_store, selection_store, policy_store)
    # Ensure we have exactly one profile
    assert policy_store.profile_count() == 1
    profile = policy_store.profiles[0]

    # 5️⃣ Generate strategy bias from the profile
    biases = generate_strategy_bias(policy_store)
    assert len(biases) == 1
    bias = biases[0]
    # Bias should equal the profile's confidence (deterministic formula)
    expected_bias_conf = (profile.success_count + 1) / (profile.success_count + profile.failure_count + 2)
    assert math.isclose(bias.bias, expected_bias_conf, rel_tol=1e-9)

    # 6️⃣ Bias‑aware plan candidate generation
    bias_plan_store = BiasPlanStore()
    exec_store = ExecutiveStore()
    update_bias_plan_candidates(
        exec_store,
        strategy_store,
        selection_store,
        policy_store,
        biases,
        bias_plan_store,
    )
    # Exactly one candidate should be present
    assert bias_plan_store.candidate_count() == 1
    candidate = bias_plan_store.candidates[0]
    # Verify IDs and deterministic composition
    expected_id = deterministic_bias_plan_candidate_id(
        goal_id=goal.id,
        strategy_id=strategy.id,
        supporting_policy_ids=candidate.supporting_policy_ids,
    )
    assert candidate.id == expected_id
    # Final score = 0.70 * base + 0.30 * bias
    expected_final = 0.70 * strategy.confidence + 0.30 * bias.bias
    assert math.isclose(candidate.final_score, expected_final, rel_tol=1e-9)
    # 7️⃣ Compute ranking – should map the goal to the created strategy
    ranking = compute_executive_ranking(bias_plan_store)
    assert ranking[goal.id] == strategy.id
