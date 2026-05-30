from __future__ import annotations

"""Immutable overload state used by the overload engine.

Only a subset of the full specification is required for deterministic unit
tests – the dataclass stores a scalar ``overload_level`` and a counter of how
many ticks the overload has persisted.
"""

from dataclasses import dataclass, replace
from typing import Tuple


@dataclass(frozen=True)
class OverloadState:
    overload_level: float = 0.0  # 0.0‑1.0 range, higher means more overload
    overload_ticks: int = 0

    def with_level(self, level: float) -> "OverloadState":
        level = max(0.0, min(1.0, level))
        return replace(self, overload_level=level)

    def with_ticks(self, ticks: int) -> "OverloadState":
        return replace(self, overload_ticks=ticks)
