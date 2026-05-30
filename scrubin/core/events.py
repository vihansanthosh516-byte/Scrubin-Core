"""Core event primitives – immutable, deterministic, replay‑safe.

All runtime code should import ``TimelineEvent`` from this module.  The class is a frozen dataclass
with a simple ``with_tick`` helper that returns a new instance via ``replace``.
"""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class TimelineEvent:
    """Immutable timeline event used throughout the simulation.

    ``tick`` – simulation tick at which the event occurred.
    ``description`` – deterministic string identifier for the event.
    """
    tick: int
    description: str

    def with_tick(self, tick: int) -> "TimelineEvent":
        return replace(self, tick=tick)
