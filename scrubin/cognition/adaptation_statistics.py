"""Deterministic statistics for adaptation profiles.

Provides aggregated metrics for analysis and replay certification.
"""

from __future__ import annotations

from .adaptation_store import AdaptationStore


def profile_count(store: AdaptationStore) -> int:
    return store.profile_count()


def mean_confidence(store: AdaptationStore) -> float:
    return store.mean_confidence()


def mean_average_delta(store: AdaptationStore) -> float:
    return store.mean_average_delta()


def adaptation_success_rate(store: AdaptationStore) -> float:
    """Overall success rate across all profiles.

    Calculated as total successful adaptations divided by total executions.
    """
    total_success = sum(p.successful_adaptations for p in store.profiles)
    total_exec = sum(p.executions for p in store.profiles)
    if total_exec == 0:
        return 0.0
    return total_success / total_exec
