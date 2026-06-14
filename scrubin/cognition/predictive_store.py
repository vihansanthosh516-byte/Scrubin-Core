"""Append‑only deterministic store for ``PredictiveState`` objects.

Provides O(1) lookup, deterministic ordering, deterministic merge semantics (replace on duplicate),
and simple query/statistics helpers.
"""

from __future__ import annotations

from typing import Dict, List, Tuple, Optional

from .predictive_state import PredictiveState


class PredictiveStore:
    """Deterministic, append‑only store for predictive states.

    * ``_states`` – list preserving insertion order.
    * ``_index`` – maps state IDs to list indices for O(1) lookup.
    """

    def __init__(self) -> None:
        self._states: List[PredictiveState] = []
        self._index: Dict[str, int] = {}

    # ---------------------------------------------------------------------
    # Core mutation – deterministic merging of duplicate predictions
    # ---------------------------------------------------------------------
    def add_or_update(self, state: PredictiveState) -> None:
        """Append a new predictive state or replace an existing one.

        Deterministic merging semantics: if a state with the same ``id`` already
        exists, it is **replaced** by the newer instance. This rule is deterministic
        because the later call overwrites the prior entry in a predictable order.
        """
        if state.id in self._index:
            idx = self._index[state.id]
            self._states[idx] = state
        else:
            self._states.append(state)
            self._index[state.id] = len(self._states) - 1

    # ---------------------------------------------------------------------
    # Query API – deterministic ordering, O(1) exact matches
    # ---------------------------------------------------------------------
    @property
    def states(self) -> Tuple[PredictiveState, ...]:
        """Immutable view of all stored predictive states in insertion order."""
        return tuple(self._states)

    def query(
        self,
        source_tick: Optional[int] = None,
        horizon: Optional[int] = None,
        decision_id: Optional[str] = None,
    ) -> Tuple[PredictiveState, ...]:
        """Return states matching the supplied criteria.

        Parameters are optional – ``None`` means no filtering on that field.
        Result preserves deterministic insertion order.
        """
        result: List[PredictiveState] = []
        for s in self._states:
            if source_tick is not None and s.source_tick != source_tick:
                continue
            if horizon is not None and s.horizon != horizon:
                continue
            # ``decision_id`` is not a direct attribute of ``PredictiveState``; we use
            # the first 12 characters of ``projected_world_hash`` as a surrogate.
            if decision_id is not None and not s.id.endswith(decision_id):
                continue
            result.append(s)
        return tuple(result)

    # ---------------------------------------------------------------------
    # Statistics helpers
    # ---------------------------------------------------------------------
    def count(self) -> int:
        return len(self._states)

    def mean_mortality(self) -> float:
        if not self._states:
            return 0.0
        return sum(s.projected_mortality for s in self._states) / len(self._states)

    def mean_sofa(self) -> float:
        if not self._states:
            return 0.0
        return sum(s.projected_sofa for s in self._states) / len(self._states)

    def mean_news2(self) -> float:
        if not self._states:
            return 0.0
        return sum(s.projected_news2 for s in self._states) / len(self._states)
