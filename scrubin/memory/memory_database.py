"""Append‑only in‑memory episode store.

Provides deterministic retrieval and simple statistics.
"""

from __future__ import annotations

from typing import List, Dict, Tuple

from .episode import Episode


class MemoryStore:
    """Immutable‑append store for Episodes.

    Episodes are stored in insertion order. Simple indexes are maintained for
    fast lookup by participant and by consequence name. The store does not
    support mutation or deletion – it mirrors an append‑only log.
    """

    def __init__(self) -> None:
        self._episodes: List[Episode] = []
        # Indexes – map key -> list of episodes (preserve order of insertion)
        self._by_participant: Dict[str, List[Episode]] = {}
        self._by_consequence: Dict[str, List[Episode]] = {}

    # ---------------------------------------------------------------------
    # Core API
    # ---------------------------------------------------------------------
    def add_episode(self, episode: Episode) -> None:
        """Append an episode and update indexes.

        Deterministic: order of addition is the sole source of ordering.
        """
        self._episodes.append(episode)
        for participant in episode.participants:
            self._by_participant.setdefault(participant, []).append(episode)
        for cons in episode.consequences:
            # Index by consequence name (``name`` field)
            self._by_consequence.setdefault(cons.name, []).append(episode)

    @property
    def episodes(self) -> Tuple[Episode, ...]:
        """Return an immutable view of all episodes in insertion order."""
        return tuple(self._episodes)

    # ---------------------------------------------------------------------
    # Simple query API – deterministic filtering
    # ---------------------------------------------------------------------
    def query(
        self,
        participant: str | None = None,
        consequence: str | None = None,
        after_tick: int | None = None,
        phase: str | None = None,
    ) -> List[Episode]:
        """Return episodes matching the supplied criteria.

        Parameters are optional – ``None`` means no filtering on that dimension.
        The result preserves the original insertion order.
        """
        if participant is not None:
            base = self._by_participant.get(participant, [])
        elif consequence is not None:
            base = self._by_consequence.get(consequence, [])
        else:
            base = self._episodes

        # Apply remaining filters
        result: List[Episode] = []
        for ep in base:
            if after_tick is not None and ep.tick <= after_tick:
                continue
            if phase is not None and ep.phase != phase:
                continue
            result.append(ep)
        return result

    # ---------------------------------------------------------------------
    # Statistics helpers
    # ---------------------------------------------------------------------
    def episode_count(self) -> int:
        return len(self._episodes)

    def mean_importance(self) -> float:
        if not self._episodes:
            return 0.0
        total = sum(ep.importance for ep in self._episodes)
        return total / len(self._episodes)
