"""Immutable deterministic executive feedback model.

Records the outcome of bias‑aware planning and measures its effectiveness.
All fields are immutable; updates are performed via ``replace``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from typing import Tuple


def deterministic_executive_feedback_id(goal_id: str, strategy_id: str) -> str:
    """Deterministic identifier for an ``ExecutiveFeedback``.

    The ID is ``feedback-`` plus the first 12 hex characters of a SHA‑256 hash over a
    canonical JSON representation of ``goal_id`` and ``strategy_id`` (tick is omitted
    to allow merging feedback for the same goal/strategy across ticks).
    """
    canonical = json.dumps(
        {"goal_id": goal_id, "strategy_id": strategy_id},
        separators=(",", ":"),
        sort_keys=True,
    )
    return f"feedback-{hashlib.sha256(canonical.encode()).hexdigest()[:12]}"


def deterministic_executive_feedback_hash(feedback: "ExecutiveFeedback") -> str:
    """Deterministic replay hash for a fully populated ``ExecutiveFeedback``.
    """
    data = {
        "id": feedback.id,
        "goal_id": feedback.goal_id,
        "strategy_id": feedback.strategy_id,
        "evaluation_score": feedback.evaluation_score,
        "policy_confidence": feedback.policy_confidence,
        "bias_used": feedback.bias_used,
        "prediction_error": feedback.prediction_error,
        "confidence_delta": feedback.confidence_delta,
        "tick": feedback.tick,
        "supporting_policy_ids": list(feedback.supporting_policy_ids),
        "supporting_evaluation_ids": list(feedback.supporting_evaluation_ids),
    }
    json_repr = json.dumps(data, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(json_repr.encode()).hexdigest()


@dataclass(frozen=True)
class ExecutiveFeedback:
    """Immutable feedback linking a goal, strategy and evaluation.

    ``policy_confidence`` – confidence from the associated ``PolicyProfile``.
    ``bias_used`` – bias score from the associated ``BiasPlanCandidate``.
    ``prediction_error`` – absolute error between policy confidence and evaluation.
    ``confidence_delta`` – raw difference (evaluation - policy confidence).
    """
    id: str
    goal_id: str
    strategy_id: str
    evaluation_score: float
    policy_confidence: float
    bias_used: float
    prediction_error: float
    confidence_delta: float
    tick: int
    supporting_policy_ids: Tuple[str, ...]
    supporting_evaluation_ids: Tuple[str, ...]
    replay_hash: str

    @staticmethod
    def create(
        goal_id: str,
        strategy_id: str,
        evaluation_score: float,
        policy_confidence: float,
        bias_used: float,
        prediction_error: float,
        confidence_delta: float,
        tick: int,
        supporting_policy_ids: Tuple[str, ...] = (),
        supporting_evaluation_ids: Tuple[str, ...] = (),
    ) -> "ExecutiveFeedback":
        """Factory that creates a deterministic ``ExecutiveFeedback``.
        """
        fb_id = deterministic_executive_feedback_id(goal_id, strategy_id)
        placeholder = ExecutiveFeedback(
            id=fb_id,
            goal_id=goal_id,
            strategy_id=strategy_id,
            evaluation_score=evaluation_score,
            policy_confidence=policy_confidence,
            bias_used=bias_used,
            prediction_error=prediction_error,
            confidence_delta=confidence_delta,
            tick=tick,
            supporting_policy_ids=supporting_policy_ids,
            supporting_evaluation_ids=supporting_evaluation_ids,
            replay_hash="",
        )
        return replace(placeholder, replay_hash=deterministic_executive_feedback_hash(placeholder))
