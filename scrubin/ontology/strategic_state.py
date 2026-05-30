from __future__ import annotations

"""Placeholder for strategic state required by some engines.

The full strategic planning subsystem is beyond the scope of this patch; a
minimal immutable dataclass satisfies type checks.
"""

from dataclasses import dataclass, field, replace
from typing import Tuple


@dataclass(frozen=True)
class StrategicState:
    # Example field – a tuple of high‑level goal identifiers.
    strategic_goals: Tuple[str, ...] = field(default_factory=tuple)

    def with_goals(self, goals: Tuple[str, ...]) -> "StrategicState":
        return replace(self, strategic_goals=goals)
