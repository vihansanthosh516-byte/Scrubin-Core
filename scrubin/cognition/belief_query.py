"""High‑level deterministic query interface for ``BeliefStore``.

Thin wrapper that forwards to ``BeliefStore.query`` – kept separate so callers
import a stable public API path.
"""

from __future__ import annotations

from typing import Tuple, Optional

from .belief_store import BeliefStore


def query_beliefs(
    store: BeliefStore,
    statement: Optional[str] = None,
    min_confidence: Optional[float] = None,
    after_tick: Optional[int] = None,
) -> Tuple:
    """Return deterministic belief query results.

    Parameters are passed directly to :meth:`BeliefStore.query`.
    """
    return store.query(
        statement=statement,
        min_confidence=min_confidence,
        after_tick=after_tick,
    )
