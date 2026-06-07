'''History engine for deterministic adaptive search – immutable records.'''
from __future__ import annotations

from typing import Tuple

from .search_models import SearchHistory


class HistoryEngine:
    """Maintains an immutable collection of SearchHistory entries.

    All modifications return a new HistoryEngine instance leaving the original untouched.
    """
    def __init__(self, histories: Tuple[SearchHistory, ...] = ()):  # type: ignore[override]
        # Store histories sorted deterministically by (experiment_id, run_id)
        self._histories = tuple(sorted(histories, key=lambda h: (h.experiment_id, h.run_id)))

    def add(self, entry: SearchHistory) -> "HistoryEngine":
        """Return a new HistoryEngine with the given entry added, preserving deterministic ordering."""
        new_histories = self._histories + (entry,)
        return HistoryEngine(new_histories)

    def get_all(self) -> Tuple[SearchHistory, ...]:
        return self._histories

    def __len__(self) -> int:
        return len(self._histories)
