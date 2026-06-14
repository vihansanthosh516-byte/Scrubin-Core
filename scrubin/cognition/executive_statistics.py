"""Deterministic statistics helpers for executive goals.

Provides aggregate metrics useful for diagnostics and testing.
"""

from __future__ import annotations

from .executive_store import ExecutiveStore


def executive_statistics(executive_store: ExecutiveStore) -> dict:
    """Return a dictionary of deterministic statistics for the executive layer.

    Keys:
        - goal_count
        - completed
        - active
        - failed
        - mean_priority
        - mean_confidence
        - completion_rate
    """
    count = executive_store.goal_count()
    status_counts = executive_store.status_counts()
    completed = status_counts.get("completed", 0)
    active = status_counts.get("active", 0)
    failed = status_counts.get("failed", 0)
    mean_priority = executive_store.mean_priority()
    mean_confidence = executive_store.mean_confidence()
    completion_rate = completed / count if count > 0 else 0.0
    return {
        "goal_count": count,
        "completed": completed,
        "active": active,
        "failed": failed,
        "mean_priority": mean_priority,
        "mean_confidence": mean_confidence,
        "completion_rate": completion_rate,
    }
