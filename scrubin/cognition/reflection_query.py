"""High‑level deterministic query interface for ``ReflectionStore``.

Thin wrapper that forwards to ``ReflectionStore.query`` – kept separate so callers
import a stable public API path.
"""

from __future__ import annotations

from typing import Tuple, Optional

from .reflection_store import ReflectionStore


def query_reflections(
    store: ReflectionStore,
    statement: Optional[str] = None,
    min_confidence: Optional[float] = None,
    after_tick: Optional[int] = None,
) -> Tuple:
    """Return deterministic reflection query results.

    Parameters are passed directly to :meth:`ReflectionStore.query`.
    """
    return store.query(
        statement=statement,
        min_confidence=min_confidence,
        after_tick=after_tick,
    )
