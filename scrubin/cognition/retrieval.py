"""Retrieval utilities for episodic memory.

Provides simple deterministic retrieval based on a single field – e.g.,
``complication`` name. More complex retrieval (semantic similarity, relevance
scoring) will be added in later phases.
"""

from __future__ import annotations

from typing import List

from scrubin.memory.memory_database import MemoryStore
from scrubin.memory.episode import Episode


def retrieve_by_complication(store: MemoryStore, complication_name: str) -> List[Episode]:
    """Return episodes that contain a consequence with the given name.

    The lookup uses the store's internal consequence index for O(1) access.
    """
    return store.query(consequence=complication_name)
