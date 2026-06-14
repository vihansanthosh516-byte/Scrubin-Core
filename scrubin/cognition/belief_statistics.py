"""Simple deterministic statistics helpers for ``BeliefStore``.

Functions compute aggregate metrics that are useful for diagnostics and for the
planner to reason about belief quality.
"""

from __future__ import annotations

from .belief_store import BeliefStore


def belief_count(store: BeliefStore) -> int:
    """Return the total number of beliefs stored."""
    return store.belief_count()


def mean_confidence(store: BeliefStore) -> float:
    """Return the mean confidence across all stored beliefs."""
    return store.mean_confidence()


def summary(store: BeliefStore):
    """Return a ``(count, mean_confidence)`` tuple for quick reporting."""
    return (belief_count(store), mean_confidence(store))
