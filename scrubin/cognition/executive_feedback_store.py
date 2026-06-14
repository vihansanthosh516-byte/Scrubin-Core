"""Append‑only deterministic store for ``ExecutiveFeedback`` objects.

Provides O(1) lookup, deterministic ordering, and merge semantics.
"""

from __future__ import annotations

from dataclasses import replace
from typing import List, Tuple, Optional, Dict

from .executive_feedback import ExecutiveFeedback, deterministic_executive_feedback_hash


class ExecutiveFeedbackStore:
    """Deterministic, append‑only store for executive feedback records.

    * ``_feedbacks`` – list preserving insertion order.
    * ``_index`` – maps feedback IDs to list indices for O(1) lookup.
    """

    def __init__(self) -> None:
        self._feedbacks: List[ExecutiveFeedback] = []
        self._index: Dict[str, int] = {}

    # ---------------------------------------------------------------------
    # Core mutation – deterministic merging of duplicate feedback entries
    # ---------------------------------------------------------------------
    def add_or_update(self, feedback: ExecutiveFeedback) -> None:
        """Append a new feedback entry or merge with an existing one.

        Merge semantics:
            * ``supporting_policy_ids`` – union (sorted).
            * ``supporting_evaluation_ids`` – union (sorted).
            * Keep higher ``evaluation_score`` and ``policy_confidence``.
            * Keep later ``tick``.
            * ``prediction_error`` and ``confidence_delta`` recomputed from stored values.
            * Recalculate deterministic replay hash.
        """
        if feedback.id in self._index:
            idx = self._index[feedback.id]
            prior = self._feedbacks[idx]
            # Union supporting IDs
            new_policies = tuple(sorted(set(prior.supporting_policy_ids) | set(feedback.supporting_policy_ids)))
            new_evals = tuple(sorted(set(prior.supporting_evaluation_ids) | set(feedback.supporting_evaluation_ids)))
            # Keep higher scores where appropriate
            eval_score = max(prior.evaluation_score, feedback.evaluation_score)
            policy_conf = max(prior.policy_confidence, feedback.policy_confidence)
            bias_used = max(prior.bias_used, feedback.bias_used)
            pred_error = max(prior.prediction_error, feedback.prediction_error)
            conf_delta = max(prior.confidence_delta, feedback.confidence_delta)
            merged = ExecutiveFeedback(
                id=prior.id,
                goal_id=prior.goal_id,
                strategy_id=prior.strategy_id,
                evaluation_score=eval_score,
                policy_confidence=policy_conf,
                bias_used=bias_used,
                prediction_error=pred_error,
                confidence_delta=conf_delta,
                tick=max(prior.tick, feedback.tick),
                supporting_policy_ids=new_policies,
                supporting_evaluation_ids=new_evals,
                replay_hash="",
            )
            merged = replace(merged, replay_hash=deterministic_executive_feedback_hash(merged))
            self._feedbacks[idx] = merged
        else:
            self._feedbacks.append(feedback)
            self._index[feedback.id] = len(self._feedbacks) - 1

    # ---------------------------------------------------------------------
    # Query API – deterministic ordering, O(1) exact matches
    # ---------------------------------------------------------------------
    @property
    def feedbacks(self) -> Tuple[ExecutiveFeedback, ...]:
        """Immutable view of all stored feedback entries in insertion order."""
        return tuple(self._feedbacks)

    def query(
        self,
        goal_id: Optional[str] = None,
        strategy_id: Optional[str] = None,
        min_tick: Optional[int] = None,
    ) -> Tuple[ExecutiveFeedback, ...]:
        """Return feedback entries matching supplied criteria.

        Parameters are optional – ``None`` means no filtering on that field.
        Result preserves deterministic insertion order.
        """
        result: List[ExecutiveFeedback] = []
        for fb in self._feedbacks:
            if goal_id is not None and fb.goal_id != goal_id:
                continue
            if strategy_id is not None and fb.strategy_id != strategy_id:
                continue
            if min_tick is not None and fb.tick <= min_tick:
                continue
            result.append(fb)
        return tuple(result)

    # ---------------------------------------------------------------------
    # Statistics helpers
    # ---------------------------------------------------------------------
    def feedback_count(self) -> int:
        return len(self._feedbacks)

    def mean_prediction_error(self) -> float:
        if not self._feedbacks:
            return 0.0
        return sum(fb.prediction_error for fb in self._feedbacks) / len(self._feedbacks)

    def mean_confidence_delta(self) -> float:
        if not self._feedbacks:
            return 0.0
        return sum(fb.confidence_delta for fb in self._feedbacks) / len(self._feedbacks)

    def summary(self) -> Tuple[int, float, float]:
        """Return ``(count, mean_prediction_error, mean_confidence_delta)``.
        """
        return (
            self.feedback_count(),
            self.mean_prediction_error(),
            self.mean_confidence_delta(),
        )
