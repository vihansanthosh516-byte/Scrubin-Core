"""Deterministic strategy selection engine.

Ranks available strategies for each executive goal using a strict, deterministic
ordering (confidence → success_count → support_count → id) and creates
``StrategySelection`` records linking goals to the chosen strategy.
"""

from __future__ import annotations

from typing import Tuple, List

from .strategy_selection import StrategySelection
from .strategy_selection_store import StrategySelectionStore
from .executive_store import ExecutiveStore
from .strategy_store import StrategyStore
from .belief_store import BeliefStore
from .reflection_store import ReflectionStore


def _rank_strategies(strategies: List["scrubin.cognition.strategy.Strategy"]) -> List["scrubin.cognition.strategy.Strategy"]:
    """Return strategies sorted by deterministic ranking criteria.

    Ranking order (descending): confidence, success_count, support_count, id.
    """
    return sorted(
        strategies,
        key=lambda s: (-s.confidence, -s.success_count, -len(s.supporting_plan_ids), s.id),
    )


def update_strategy_selection(
    executive_store: ExecutiveStore,
    strategy_store: StrategyStore,
    belief_store: BeliefStore,
    reflection_store: ReflectionStore,
    selection_store: StrategySelectionStore,
) -> None:
    """Select deterministic strategies for each executive goal.

    For every goal in ``executive_store``, the highest‑ranked strategy is chosen.
    The resulting ``StrategySelection`` objects are added to ``selection_store``.
    """
    # Pre‑rank strategies once for efficiency
    ranked_strategies = _rank_strategies(list(strategy_store.strategies))
    if not ranked_strategies:
        return
    best_strategy = ranked_strategies[0]

    for goal in executive_store.goals:
        # Simple deterministic selection: use the globally best strategy.
        # In a more elaborate system we could filter by relevance, but this
        # satisfies the deterministic ranking requirement.
        selection = StrategySelection.create(
            goal_id=goal.id,
            strategy_id=best_strategy.id,
            score=best_strategy.confidence,
            selection_reason="Highest confidence strategy",
            supporting_strategy_ids=(best_strategy.id,),
            supporting_belief_ids=(),
            supporting_reflection_ids=(),
            tick=goal.created_tick,
        )
        selection_store.add_or_update(selection)
