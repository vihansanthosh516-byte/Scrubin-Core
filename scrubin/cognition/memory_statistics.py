"""Simple statistics utilities for episodic memory.

These functions operate on a :class:`scrubin.memory.memory_database.MemoryStore`
instance and return deterministic aggregates.
"""

from __future__ import annotations

from typing import Tuple

from scrubin.memory.memory_database import MemoryStore


def episode_count(store: MemoryStore) -> int:
    """Return the total number of episodes stored."""
    return store.episode_count()


def mean_importance(store: MemoryStore) -> float:
    """Return the mean importance across all stored episodes."""
    return store.mean_importance()


def summary(store: MemoryStore) -> Tuple[int, float]:
    """Return a ``(count, mean_importance)`` tuple for quick reporting."""
    return (episode_count(store), mean_importance(store))
