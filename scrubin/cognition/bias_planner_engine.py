"""Deterministic bias‑aware planner engine.

Generates ``BiasPlanCandidate`` objects by combining strategy confidence with the
learned bias from policy profiles. All operations are pure cognition – no world
mutation.
"""

from __future__ import annotations

from typing import List, Dict

from .bias_plan_candidate import BiasPlanCandidate
from .bias_plan_store import BiasPlanStore
from .strategy import Strategy
from .strategy_store import StrategyStore
from .strategy_selection_store import StrategySelectionStore
from .policy_store import PolicyStore
from .strategy_bias import StrategyBias


def _lookup_strategy_confidence(
    strategy_id: str, strategy_map: Dict[str, Strategy]
) -> float:
    """Return the confidence of a strategy, defaulting to ``0.0`` if missing."""
    return strategy_map.get(strategy_id).confidence if strategy_id in strategy_map else 0.0


def _lookup_bias_for_strategy(
    strategy_id: str, bias_list: List[StrategyBias]
) -> float:
    """Return the highest bias score associated with a strategy.

    If a strategy has multiple ``StrategyBias`` entries (e.g., from multiple
    policy profiles), the deterministic choice is the maximum bias value.
    Returns ``0.0`` when no bias exists.
    """
    relevant = [b for b in bias_list if b.strategy_id == strategy_id]
    if not relevant:
        return 0.0
    # Deterministic selection – highest bias; ties resolve by deterministic ID order.
    max_bias = max(relevant, key=lambda b: (b.bias, b.id))
    return max_bias.bias


def update_bias_plan_candidates(
    executive_store: "scrubin.cognition.executive_store.ExecutiveStore",
    strategy_store: StrategyStore,
    selection_store: StrategySelectionStore,
    policy_store: PolicyStore,
    strategy_biases: List[StrategyBias],
    plan_store: BiasPlanStore,
) -> None:
    """Create or update ``BiasPlanCandidate`` objects for each goal‑strategy pair.

    For every ``StrategySelection`` entry we compute:
        base_score = strategy confidence
        bias_score = highest bias for that strategy
        final_score = 0.70 * base_score + 0.30 * bias_score
    The candidate aggregates supporting IDs and is stored in ``plan_store`` using
    its deterministic ``add_or_update`` method.
    """
    # Build quick look‑ups
    strategy_map = {s.id: s for s in strategy_store.strategies}
    # Index selections for O(1) access per goal
    for selection in selection_store.selections:
        goal_id = selection.goal_id
        strategy_id = selection.strategy_id
        base = _lookup_strategy_confidence(strategy_id, strategy_map)
        bias = _lookup_bias_for_strategy(strategy_id, strategy_biases)
        final = 0.70 * base + 0.30 * bias
        # Supporting IDs: policies that contributed to bias (if any)
        supporting_policies = tuple(
            b.supporting_policy_ids[0] for b in strategy_biases if b.strategy_id == strategy_id
        )
        candidate = BiasPlanCandidate.create(
            goal_id=goal_id,
            strategy_id=strategy_id,
            base_score=base,
            bias_score=bias,
            final_score=final,
            supporting_policy_ids=supporting_policies,
            supporting_strategy_ids=(strategy_id,),
            supporting_goal_ids=(goal_id,),
        )
        plan_store.add_or_update(candidate)
