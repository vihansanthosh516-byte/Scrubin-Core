"""Deterministic statistics helpers for ``Plan`` collections.

Provides aggregate metrics used by diagnostics and testing.
"""

from __future__ import annotations

from .plan_store import PlanStore


def plan_statistics(plan_store: PlanStore) -> dict:
    """Return a dictionary of deterministic statistics for the given store.

    Keys:
        - plan_count
        - mean_score
        - max_score
        - mean_confidence
        - average_horizon
    """
    count, mean_score, max_score, mean_conf, avg_horizon = plan_store.summary()
    return {
        "plan_count": count,
        "mean_score": mean_score,
        "max_score": max_score,
        "mean_confidence": mean_conf,
        "average_horizon": avg_horizon,
    }
