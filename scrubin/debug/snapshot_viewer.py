# Snapshot viewer – human‑readable inspection of world snapshots.
"""
Provides a ``SnapshotViewer`` utility that can pretty‑print a ``WorldState``
(or compatible dict) and optionally show a shallow diff between two snapshots.
The implementation is lightweight and avoids mutating any state.
"""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from typing import Any, Dict


class SnapshotViewer:
    """Utility for displaying world snapshots.

    Methods
    -------
    pretty(state)
        Return a formatted JSON string representing ``state``.
    diff(state_a, state_b)
        Return a shallow diff (top‑level fields) between two states as a JSON string.
    """

    @staticmethod
    def _to_dict(state: Any) -> Dict:
        """Convert ``state`` to a plain ``dict``.

        Handles ``dataclass`` instances via ``asdict`` and passes through dicts
        unchanged. Raises ``TypeError`` for unsupported types.
        """
        if is_dataclass(state):
            return asdict(state)
        if isinstance(state, dict):
            return state
        raise TypeError(f"Unsupported state type: {type(state)}")

    @staticmethod
    def pretty(state: Any) -> str:
        """Return a nicely indented JSON representation of ``state``.
        """
        data = SnapshotViewer._to_dict(state)
        return json.dumps(data, indent=2, sort_keys=True)

    @staticmethod
    def diff(state_a: Any, state_b: Any) -> str:
        """Return a shallow diff between two states as a JSON string.

        The diff maps each differing top‑level key to a sub‑mapping ``{"a": val_a,
        "b": val_b}``.
        """
        a = SnapshotViewer._to_dict(state_a)
        b = SnapshotViewer._to_dict(state_b)
        keys = set(a.keys()) | set(b.keys())
        diff: Dict[str, Dict[str, Any]] = {}
        for k in keys:
            av = a.get(k)
            bv = b.get(k)
            if av != bv:
                diff[k] = {"a": av, "b": bv}
        return json.dumps(diff, indent=2, sort_keys=True)
