"""Immutable deterministic executive evaluation model.

Represents a deterministic assessment of an executive goal, its selected
strategy, and supporting cognition artifacts.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from typing import Tuple


def deterministic_executive_evaluation_id(
    goal_id: str,
    strategy_id: str,
    selection_id: str,
    tick: int,
) -> str:
    """Deterministic identifier for an ``ExecutiveEvaluation``.

    The ID is ``eval-`` plus the first 12 hex characters of a SHA‑256 hash over a
    canonical JSON representation of the goal, strategy, selection and tick.
    """
    canonical = json.dumps(
        {
            "goal_id": goal_id,
            "strategy_id": strategy_id,
            "selection_id": selection_id,
            "tick": tick,
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    return f"eval-{hashlib.sha256(canonical.encode()).hexdigest()[:12]}"


def deterministic_executive_evaluation_hash(evaluation: "ExecutiveEvaluation") -> str:
    """Deterministic replay hash for a fully populated ``ExecutiveEvaluation``.
    """
    data = {
        "id": evaluation.id,
        "goal_id": evaluation.goal_id,
        "strategy_id": evaluation.strategy_id,
        "selection_id": evaluation.selection_id,
        "evaluation_score": evaluation.evaluation_score,
        "outcome_score": evaluation.outcome_score,
        "confidence_score": evaluation.confidence_score,
        "supporting_episode_ids": list(evaluation.supporting_episode_ids),
        "supporting_fact_ids": list(evaluation.supporting_fact_ids),
        "supporting_belief_ids": list(evaluation.supporting_belief_ids),
        "supporting_reflection_ids": list(evaluation.supporting_reflection_ids),
        "supporting_counterfactual_ids": list(evaluation.supporting_counterfactual_ids),
        "tick": evaluation.tick,
    }
    json_repr = json.dumps(data, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(json_repr.encode()).hexdigest()


@dataclass(frozen=True)
class ExecutiveEvaluation:
    """Immutable deterministic evaluation of an executive decision.
    """
    id: str
    goal_id: str
    strategy_id: str
    selection_id: str
    evaluation_score: float
    outcome_score: float
    confidence_score: float
    supporting_episode_ids: Tuple[str, ...]
    supporting_fact_ids: Tuple[str, ...]
    supporting_belief_ids: Tuple[str, ...]
    supporting_reflection_ids: Tuple[str, ...]
    supporting_counterfactual_ids: Tuple[str, ...]
    tick: int
    replay_hash: str

    @staticmethod
    def create(
        goal_id: str,
        strategy_id: str,
        selection_id: str,
        evaluation_score: float,
        outcome_score: float,
        confidence_score: float,
        supporting_episode_ids: Tuple[str, ...] = (),
        supporting_fact_ids: Tuple[str, ...] = (),
        supporting_belief_ids: Tuple[str, ...] = (),
        supporting_reflection_ids: Tuple[str, ...] = (),
        supporting_counterfactual_ids: Tuple[str, ...] = (),
        tick: int = 0,
    ) -> "ExecutiveEvaluation":
        """Factory that creates a deterministic ``ExecutiveEvaluation``.
        """
        eval_id = deterministic_executive_evaluation_id(goal_id, strategy_id, selection_id, tick)
        placeholder = ExecutiveEvaluation(
            id=eval_id,
            goal_id=goal_id,
            strategy_id=strategy_id,
            selection_id=selection_id,
            evaluation_score=evaluation_score,
            outcome_score=outcome_score,
            confidence_score=confidence_score,
            supporting_episode_ids=supporting_episode_ids,
            supporting_fact_ids=supporting_fact_ids,
            supporting_belief_ids=supporting_belief_ids,
            supporting_reflection_ids=supporting_reflection_ids,
            supporting_counterfactual_ids=supporting_counterfactual_ids,
            tick=tick,
            replay_hash="",
        )
        return replace(placeholder, replay_hash=deterministic_executive_evaluation_hash(placeholder))
