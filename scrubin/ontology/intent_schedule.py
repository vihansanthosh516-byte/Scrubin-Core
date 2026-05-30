from __future__ import annotations

"""Immutable schedule of intents for deterministic execution arbitration.

The schedule mirrors the events emitted by the intent scheduler – executable,
blocked, deferred and interrupted intents are stored as tuples of intent IDs.
"""

from dataclasses import dataclass, field, replace
from typing import Tuple


@dataclass(frozen=True)
class IntentSchedule:
    executable_intents: Tuple[str, ...] = field(default_factory=tuple)
    blocked_intents: Tuple[str, ...] = field(default_factory=tuple)
    deferred_intents: Tuple[str, ...] = field(default_factory=tuple)
    interrupted_intents: Tuple[str, ...] = field(default_factory=tuple)
    schedule_tick: int = 0

    def with_executable(self, ids: Tuple[str, ...]) -> "IntentSchedule":
        return replace(self, executable_intents=ids)

    def with_blocked(self, ids: Tuple[str, ...]) -> "IntentSchedule":
        return replace(self, blocked_intents=ids)

    def with_deferred(self, ids: Tuple[str, ...]) -> "IntentSchedule":
        return replace(self, deferred_intents=ids)

    def with_interrupted(self, ids: Tuple[str, ...]) -> "IntentSchedule":
        return replace(self, interrupted_intents=ids)

    def with_tick(self, tick: int) -> "IntentSchedule":
        return replace(self, schedule_tick=tick)
