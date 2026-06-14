"""Immutable deterministic executive policy decision model.

Aggregates all executive learning signals to produce a final arbitration
decision for each executive goal. All fields are frozen; updates use
``replace``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from typing import Tuple


def deterministic_executive_policy_decision_id(goal_id: str, selected_strategy_id: str) -> str:
    """Deterministic identifier for an ``ExecutivePolicyDecision``.

    The ID is ``policydec-`` plus the first 12 hex characters of a SHA‑256 hash over a
    canonical JSON representation of ``goal_id`` and ``selected_strategy_id``.
    """
    canonical = json.dumps(
        {"goal_id": goal_id, "selected_strategy_id": selected_strategy_id},
        separators=(",", ":"),
        sort_keys=True,
    )
    return f"policydec-{hashlib.sha256(canonical.encode()).hexdigest()[:12]}"


def deterministic_executive_policy_decision_hash(decision: "ExecutivePolicyDecision") -> str:
    """Deterministic replay hash for a fully populated ``ExecutivePolicyDecision``.
    """
    data = {
        "id": decision.id,
        "goal_id": decision.goal_id,
        "selected_strategy_id": decision.selected_strategy_id,
        "arbitration_score": decision.arbitration_score,
        "confidence": decision.confidence,
        "rejected_strategy_ids": list(decision.rejected_strategy_ids),
        "supporting_strategy_selection_ids": list(decision.supporting_strategy_selection_ids),
        "supporting_policy_profile_ids": list(decision.supporting_policy_profile_ids),
        "supporting_adaptation_profile_ids": list(decision.supporting_adaptation_profile_ids),
        "supporting_optimization_ids": list(decision.supporting_optimization_ids),
        "supporting_signal_ids": list(decision.supporting_signal_ids),
        "first_seen_tick": decision.first_seen_tick,
        "last_seen_tick": decision.last_seen_tick,
    }
    json_repr = json.dumps(data, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(json_repr.encode()).hexdigest()


@dataclass(frozen=True)
class ExecutivePolicyDecision:
    """Immutable arbitration decision for an executive goal.

    ``rejected_strategy_ids`` – strategies considered but not selected.
    ``supporting_*_ids`` – IDs of the underlying records that contributed to the
    decision.
    """
    id: str
    goal_id: str
    selected_strategy_id: str
    arbitration_score: float
    confidence: float
    rejected_strategy_ids: Tuple[str, ...]
    supporting_strategy_selection_ids: Tuple[str, ...]
    supporting_policy_profile_ids: Tuple[str, ...]
    supporting_adaptation_profile_ids: Tuple[str, ...]
    supporting_optimization_ids: Tuple[str, ...]
    supporting_signal_ids: Tuple[str, ...]
    first_seen_tick: int
    last_seen_tick: int
    replay_hash: str

    @staticmethod
    def create(
        goal_id: str,
        selected_strategy_id: str,
        arbitration_score: float,
        confidence: float,
        rejected_strategy_ids: Tuple[str, ...] = (),
        supporting_strategy_selection_ids: Tuple[str, ...] = (),
        supporting_policy_profile_ids: Tuple[str, ...] = (),
        supporting_adaptation_profile_ids: Tuple[str, ...] = (),
        supporting_optimization_ids: Tuple[str, ...] = (),
        supporting_signal_ids: Tuple[str, ...] = (),
        first_seen_tick: int = 0,
        last_seen_tick: int = 0,
    ) -> "ExecutivePolicyDecision":
        """Factory that creates a deterministic ``ExecutivePolicyDecision``.
        """
        dec_id = deterministic_executive_policy_decision_id(goal_id, selected_strategy_id)
        placeholder = ExecutivePolicyDecision(
            id=dec_id,
            goal_id=goal_id,
            selected_strategy_id=selected_strategy_id,
            arbitration_score=arbitration_score,
            confidence=confidence,
            rejected_strategy_ids=rejected_strategy_ids,
            supporting_strategy_selection_ids=supporting_strategy_selection_ids,
            supporting_policy_profile_ids=supporting_policy_profile_ids,
            supporting_adaptation_profile_ids=supporting_adaptation_profile_ids,
            supporting_optimization_ids=supporting_optimization_ids,
            supporting_signal_ids=supporting_signal_ids,
            first_seen_tick=first_seen_tick,
            last_seen_tick=last_seen_tick,
            replay_hash="",
        )
        return replace(placeholder, replay_hash=deterministic_executive_policy_decision_hash(placeholder))
