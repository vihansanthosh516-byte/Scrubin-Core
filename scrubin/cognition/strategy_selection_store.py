"""Append‑only deterministic store for ``StrategySelection`` objects.

Provides O(1) lookup by selection ID and deterministic query ordering.
"""

from __future__ import annotations

from dataclasses import replace
from typing import List, Tuple, Optional, Dict

from .strategy_selection import StrategySelection, deterministic_selection_hash


class StrategySelectionStore:
    """Deterministic, append‑only store for strategy selections.

    * ``_selections`` – list preserving insertion order.
    * ``_index`` – maps selection IDs to list indices for O(1) lookup.
    """

    def __init__(self) -> None:
        self._selections: List[StrategySelection] = []
        self._index: Dict[str, int] = {}

    # ---------------------------------------------------------------------
    # Core mutation – deterministic merging of duplicate selections
    # ---------------------------------------------------------------------
    def add_or_update(self, selection: StrategySelection) -> None:
        """Append a new selection or merge with an existing one.

        When a duplicate ID is encountered, supporting IDs are unioned, the
        higher score is retained, and the tick is updated to the later value.
        The merged object receives a new deterministic replay hash.
        """
        if selection.id in self._index:
            idx = self._index[selection.id]
            prior = self._selections[idx]
            # Merge supporting IDs
            new_strat_ids = tuple(sorted(set(prior.supporting_strategy_ids) | set(selection.supporting_strategy_ids)))
            new_belief_ids = tuple(sorted(set(prior.supporting_belief_ids) | set(selection.supporting_belief_ids)))
            new_reflection_ids = tuple(sorted(set(prior.supporting_reflection_ids) | set(selection.supporting_reflection_ids)))
            # Determine higher score
            new_score = max(prior.score, selection.score)
            # Choose later tick
            new_tick = max(prior.tick, selection.tick)
            merged = StrategySelection(
                id=prior.id,
                goal_id=prior.goal_id,
                strategy_id=prior.strategy_id,
                score=new_score,
                selection_reason=prior.selection_reason,
                supporting_strategy_ids=new_strat_ids,
                supporting_belief_ids=new_belief_ids,
                supporting_reflection_ids=new_reflection_ids,
                tick=new_tick,
                replay_hash="",
            )
            merged = replace(merged, replay_hash=deterministic_selection_hash(merged))
            self._selections[idx] = merged
        else:
            self._selections.append(selection)
            self._index[selection.id] = len(self._selections) - 1

    # ---------------------------------------------------------------------
    # Query API – deterministic ordering, O(1) exact matches
    # ---------------------------------------------------------------------
    @property
    def selections(self) -> Tuple[StrategySelection, ...]:
        """Immutable view of all stored selections in insertion order."""
        return tuple(self._selections)

    def query(
        self,
        goal_id: Optional[str] = None,
        strategy_id: Optional[str] = None,
        min_score: Optional[float] = None,
    ) -> Tuple[StrategySelection, ...]:
        """Return selections matching the supplied criteria.

        Parameters are optional – ``None`` means no filtering on that field.
        The result preserves deterministic insertion order.
        """
        result: List[StrategySelection] = []
        for s in self._selections:
            if goal_id is not None and s.goal_id != goal_id:
                continue
            if strategy_id is not None and s.strategy_id != strategy_id:
                continue
            if min_score is not None and s.score < min_score:
                continue
            result.append(s)
        return tuple(result)

    # ---------------------------------------------------------------------
    # Statistics helpers
    # ---------------------------------------------------------------------
    def selection_count(self) -> int:
        return len(self._selections)

    def mean_score(self) -> float:
        if not self._selections:
            return 0.0
        return sum(s.score for s in self._selections) / len(self._selections)

    def summary(self) -> Tuple[int, float]:
        """Return ``(count, mean_score)``.
        """
        return (self.selection_count(), self.mean_score())
