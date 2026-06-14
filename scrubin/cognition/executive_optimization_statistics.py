"""Deterministic statistics for executive optimizations.

Provides aggregated metrics for analysis and replay certification.
"""

from __future__ import annotations

from .executive_optimization_store import ExecutiveOptimizationStore
from collections import Counter


def optimization_count(store: ExecutiveOptimizationStore) -> int:
    return store.optimization_count()


def mean_score(store: ExecutiveOptimizationStore) -> float:
    return store.mean_score()


def mean_confidence(store: ExecutiveOptimizationStore) -> float:
    return store.mean_confidence()


def recommendation_distribution(store: ExecutiveOptimizationStore) -> dict:
    """Return a dict mapping recommendation strings to their occurrence count."""
    counter = Counter(opt.recommendation for opt in store.optimizations)
    return dict(counter)


def strengthen_ratio(store: ExecutiveOptimizationStore) -> float:
    total = store.optimization_count()
    if total == 0:
        return 0.0
    strengthen = sum(1 for opt in store.optimizations if opt.recommendation == "strengthen")
    return strengthen / total


def retire_ratio(store: ExecutiveOptimizationStore) -> float:
    total = store.optimization_count()
    if total == 0:
        return 0.0
    retire = sum(1 for opt in store.optimizations if opt.recommendation == "retire")
    return retire / total
