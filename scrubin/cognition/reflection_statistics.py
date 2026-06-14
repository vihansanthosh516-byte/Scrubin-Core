"""Simple deterministic statistics helpers for ``ReflectionStore``.

Functions compute aggregate metrics that are useful for diagnostics and for the
planner to reason about reflection quality.
"""

from __future__ import annotations

from .reflection_store import ReflectionStore


def reflection_count(store: ReflectionStore) -> int:
    """Return the total number of reflections stored."""
    return store.reflection_count()


def mean_confidence(store: ReflectionStore) -> float:
    """Return the mean confidence across all stored reflections."""
    return store.mean_confidence()


def mean_support(store: ReflectionStore) -> float:
    """Return the mean support count across all stored reflections."""
    return store.mean_support()


def max_support(store: ReflectionStore) -> int:
    """Return the maximum support count among stored reflections."""
    return store.max_support()


def summary(store: ReflectionStore):
    """Return a ``(count, mean_confidence, mean_support, max_support)`` tuple."""
    return store.summary()
