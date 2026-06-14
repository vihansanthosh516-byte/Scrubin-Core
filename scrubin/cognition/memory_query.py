"""High‑level query interface for episodic memory.

Provides a thin wrapper around :class:`scrubin.memory.memory_database.MemoryStore`
that can be extended with richer query languages later.
"""

from __future__ import annotations

from typing import List, Optional

from scrubin.memory.memory_database import MemoryStore
from scrubin.memory.episode import Episode


def query_memory(
    store: MemoryStore,
    participant: Optional[str] = None,
    consequence: Optional[str] = None,
    after_tick: Optional[int] = None,
    phase: Optional[str] = None,
) -> List[Episode]:
    """Return episodes matching the supplied criteria.

    Parameters are passed directly to :meth:`MemoryStore.query`.
    """
    return store.query(
        participant=participant,
        consequence=consequence,
        after_tick=after_tick,
        phase=phase,
    )
