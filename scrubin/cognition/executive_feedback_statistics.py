"""Deterministic statistics for executive feedback records.

Provides simple aggregated metrics for analysis and replay certification.
"""

from __future__ import annotations

from .executive_feedback_store import ExecutiveFeedbackStore


def feedback_count(store: ExecutiveFeedbackStore) -> int:
    return store.feedback_count()


def mean_prediction_error(store: ExecutiveFeedbackStore) -> float:
    return store.mean_prediction_error()


def mean_confidence_delta(store: ExecutiveFeedbackStore) -> float:
    return store.mean_confidence_delta()


def positive_adjustments(store: ExecutiveFeedbackStore) -> int:
    """Count feedback entries with a positive confidence delta."""
    return sum(1 for fb in store.feedbacks if fb.confidence_delta > 0)


def negative_adjustments(store: ExecutiveFeedbackStore) -> int:
    """Count feedback entries with a negative confidence delta."""
    return sum(1 for fb in store.feedbacks if fb.confidence_delta < 0)
