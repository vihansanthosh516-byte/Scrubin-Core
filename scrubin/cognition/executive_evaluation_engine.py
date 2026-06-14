"""Deterministic executive evaluation engine.

Generates ``ExecutiveEvaluation`` objects that assess the quality of an executive
decision based on deterministic signals from beliefs, reflections, and
counterfactual outcomes.
"""

from __future__ import annotations

from typing import Tuple, List

from .executive_evaluation import ExecutiveEvaluation
from .executive_evaluation_store import ExecutiveEvaluationStore
from .strategy_selection_store import StrategySelectionStore
from .executive_store import ExecutiveStore
from .strategy_store import StrategyStore
from .belief_store import BeliefStore
from .reflection_store import ReflectionStore
from .counterfactual_store import CounterfactualStore


def _average_counterfactual_success(counterfactual_store: CounterfactualStore) -> float:
    """Compute deterministic average confidence of counterfactual results.

    If there are no results, returns ``0.0``.
    """
    results = counterfactual_store.results()
    if not results:
        return 0.0
    total = sum(r.confidence for r in results)
    return total / len(results)


def update_executive_evaluations(
    selection_store: StrategySelectionStore,
    executive_store: ExecutiveStore,
    plan_store: "scrubin.planner.plan_store.PlanStore",
    strategy_store: StrategyStore,
    belief_store: BeliefStore,
    reflection_store: ReflectionStore,
    counterfactual_store: CounterfactualStore,
    evaluation_store: ExecutiveEvaluationStore,
) -> None:
    """Generate deterministic evaluations for each strategy selection.

    The evaluation score combines:
        0.35 × strategy confidence
        0.30 × mean belief confidence
        0.20 × mean reflection confidence
        0.15 × average counterfactual result confidence
    """
    belief_conf = belief_store.mean_confidence()
    reflection_conf = reflection_store.mean_confidence()
    cf_success = _average_counterfactual_success(counterfactual_store)

    # Map strategies for fast lookup
    strategy_map = {s.id: s for s in strategy_store.strategies}
    # Map executive goals for outcome
    goal_map = {g.id: g for g in executive_store.goals}

    for selection in selection_store.selections:
        # Retrieve related strategy and goal
        strategy = strategy_map.get(selection.strategy_id)
        goal = goal_map.get(selection.goal_id)
        if strategy is None or goal is None:
            continue
        # Deterministic evaluation score
        evaluation_score = (
            0.35 * strategy.confidence
            + 0.30 * belief_conf
            + 0.20 * reflection_conf
            + 0.15 * cf_success
        )
        # Outcome score: 1.0 if goal completed, else 0.0
        outcome_score = 1.0 if getattr(goal, "status", "") == "completed" else 0.0
        # Confidence score – here we simply reuse evaluation_score
        confidence_score = evaluation_score
        # Create evaluation
        eval_obj = ExecutiveEvaluation.create(
            goal_id=goal.id,
            strategy_id=strategy.id,
            selection_id=selection.id,
            evaluation_score=evaluation_score,
            outcome_score=outcome_score,
            confidence_score=confidence_score,
            supporting_episode_ids=(),
            supporting_fact_ids=(),
            supporting_belief_ids=(),
            supporting_reflection_ids=(),
            supporting_counterfactual_ids=(),
            tick=goal.created_tick,
        )
        evaluation_store.add_or_update(eval_obj)
