"""Immutable deterministic bias plan candidate model.

Represents a candidate plan for an executive goal that incorporates both the
strategy's inherent confidence and the learned bias from policy profiles.
All fields are immutable; updates use ``replace``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from typing import Tuple


def deterministic_bias_plan_candidate_id(
    goal_id: str,
    strategy_id: str,
    supporting_policy_ids: Tuple[str, ...] = (),
) -> str:
    """Deterministic identifier for a ``BiasPlanCandidate``.

    The ID is ``biasplan-`` plus the first 12 hex characters of a SHA‑256 hash
    over a canonical JSON representation of ``goal_id``, ``strategy_id`` and a
    sorted list of supporting policy IDs.
    """
    canonical = json.dumps(
        {
            "goal_id": goal_id,
            "strategy_id": strategy_id,
            "supporting_policy_ids": sorted(supporting_policy_ids),
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    return f"biasplan-{hashlib.sha256(canonical.encode()).hexdigest()[:12]}"


def deterministic_bias_plan_candidate_hash(candidate: "BiasPlanCandidate") -> str:
    """Deterministic replay hash for a fully populated ``BiasPlanCandidate``.
    """
    data = {
        "id": candidate.id,
        "goal_id": candidate.goal_id,
        "strategy_id": candidate.strategy_id,
        "base_score": candidate.base_score,
        "bias_score": candidate.bias_score,
        "final_score": candidate.final_score,
        "supporting_policy_ids": list(candidate.supporting_policy_ids),
        "supporting_strategy_ids": list(candidate.supporting_strategy_ids),
        "supporting_goal_ids": list(candidate.supporting_goal_ids),
    }
    json_repr = json.dumps(data, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(json_repr.encode()).hexdigest()


@dataclass(frozen=True)
class BiasPlanCandidate:
    """Immutable candidate linking a goal to a strategy with bias‑aware scoring.

    ``base_score`` – the strategy's confidence (pre‑bias).
    ``bias_score`` – the bias derived from policy profiles.
    ``final_score`` – weighted combination used for ranking.
    """
    id: str
    goal_id: str
    strategy_id: str
    base_score: float
    bias_score: float
    final_score: float
    supporting_policy_ids: Tuple[str, ...]
    supporting_strategy_ids: Tuple[str, ...]
    supporting_goal_ids: Tuple[str, ...]
    replay_hash: str

    @staticmethod
    def create(
        goal_id: str,
        strategy_id: str,
        base_score: float,
        bias_score: float,
        final_score: float,
        supporting_policy_ids: Tuple[str, ...] = (),
        supporting_strategy_ids: Tuple[str, ...] = (),
        supporting_goal_ids: Tuple[str, ...] = (),
    ) -> "BiasPlanCandidate":
        """Factory that creates a deterministic ``BiasPlanCandidate``.
        """
        candidate_id = deterministic_bias_plan_candidate_id(goal_id, strategy_id, supporting_policy_ids)
        placeholder = BiasPlanCandidate(
            id=candidate_id,
            goal_id=goal_id,
            strategy_id=strategy_id,
            base_score=base_score,
            bias_score=bias_score,
            final_score=final_score,
            supporting_policy_ids=supporting_policy_ids,
            supporting_strategy_ids=supporting_strategy_ids,
            supporting_goal_ids=supporting_goal_ids,
            replay_hash="",
        )
        return replace(placeholder, replay_hash=deterministic_bias_plan_candidate_hash(placeholder))
