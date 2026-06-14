"""Immutable deterministic strategy selection model.

A ``StrategySelection`` links an executive goal to a learned strategy, records a
ranking score and the deterministic reason for the choice. Instances are
immutable; updates are performed via ``replace``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from typing import Tuple


def deterministic_selection_id(goal_id: str, strategy_id: str, supporting_strategy_ids: Tuple[str, ...]) -> str:
    """Deterministic identifier for a ``StrategySelection``.

    The ID is ``sel-`` plus the first 12 hex characters of a SHA‑256 hash over a
    canonical JSON representation of the goal, the chosen strategy and the sorted
    list of supporting strategy IDs.
    """
    canonical = json.dumps(
        {
            "goal_id": goal_id,
            "strategy_id": strategy_id,
            "supporting_strategy_ids": sorted(supporting_strategy_ids),
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    return f"sel-{hashlib.sha256(canonical.encode()).hexdigest()[:12]}"


def deterministic_selection_hash(selection: "StrategySelection") -> str:
    """Deterministic replay hash for a fully populated ``StrategySelection``.
    """
    data = {
        "id": selection.id,
        "goal_id": selection.goal_id,
        "strategy_id": selection.strategy_id,
        "score": selection.score,
        "selection_reason": selection.selection_reason,
        "supporting_strategy_ids": list(selection.supporting_strategy_ids),
        "supporting_belief_ids": list(selection.supporting_belief_ids),
        "supporting_reflection_ids": list(selection.supporting_reflection_ids),
        "tick": selection.tick,
    }
    json_repr = json.dumps(data, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(json_repr.encode()).hexdigest()


@dataclass(frozen=True)
class StrategySelection:
    """Immutable link between an ``ExecutiveGoal`` and a ``Strategy``.

    ``score`` is a deterministic value (e.g., confidence) used for ranking.
    """
    id: str
    goal_id: str
    strategy_id: str
    score: float
    selection_reason: str
    supporting_strategy_ids: Tuple[str, ...]
    supporting_belief_ids: Tuple[str, ...]
    supporting_reflection_ids: Tuple[str, ...]
    tick: int
    replay_hash: str

    @staticmethod
    def create(
        goal_id: str,
        strategy_id: str,
        score: float,
        selection_reason: str,
        supporting_strategy_ids: Tuple[str, ...] = (),
        supporting_belief_ids: Tuple[str, ...] = (),
        supporting_reflection_ids: Tuple[str, ...] = (),
        tick: int = 0,
    ) -> "StrategySelection":
        """Factory that creates a deterministic ``StrategySelection``.
        """
        sel_id = deterministic_selection_id(goal_id, strategy_id, supporting_strategy_ids)
        placeholder = StrategySelection(
            id=sel_id,
            goal_id=goal_id,
            strategy_id=strategy_id,
            score=score,
            selection_reason=selection_reason,
            supporting_strategy_ids=supporting_strategy_ids,
            supporting_belief_ids=supporting_belief_ids,
            supporting_reflection_ids=supporting_reflection_ids,
            tick=tick,
            replay_hash="",
        )
        return replace(placeholder, replay_hash=deterministic_selection_hash(placeholder))
