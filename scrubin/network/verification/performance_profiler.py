"""Network Performance Profiler – records deterministic performance metrics per tick.

The profiler is read‑only: it records timings, memory usage, and queue depth but
does not affect the simulation.  All data structures are immutable.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from typing import Tuple, Dict, List

# ---------------------------------------------------------------------------
# Immutable performance record
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class PerformanceProfile:
    """Immutable snapshot of performance metrics for a single tick.

    * tick – Simulation tick number.
    * stage_durations_ms – Mapping ``stage_name -> duration_ms``.
    * memory_usage_bytes – Process memory usage at end of tick.
    * event_queue_depth – Approximate depth (placeholder – set to 0).
    """
    tick: int
    stage_durations_ms: Tuple[Tuple[str, float], ...]
    memory_usage_bytes: int
    event_queue_depth: int
    deterministic_id: str = field(init=False)

    def __post_init__(self) -> None:
        # Deterministic ID based on canonical string representation.
        stages_str = "|".join(f"{name}:{duration:.3f}" for name, duration in self.stage_durations_ms)
        text = f"{self.tick}|{stages_str}|{self.memory_usage_bytes}|{self.event_queue_depth}"
        object.__setattr__(self, "deterministic_id", hashlib.sha256(text.encode()).hexdigest())


# ---------------------------------------------------------------------------
# Profiler implementation
# ---------------------------------------------------------------------------

class NetworkPerformanceProfiler:
    """Collects deterministic performance profiles for each network tick.

    The ``record_tick`` method should be called after the execution plan has
    completed for the current tick.  It returns a ``PerformanceProfile`` and
    stores it internally for later inspection.
    """

    def __init__(self) -> None:
        self.profiles: List[PerformanceProfile] = []

    def record_tick(self, tick: int, stage_durations: Dict[str, float]) -> PerformanceProfile:
        # Convert dict to sorted tuple for deterministic ordering.
        sorted_items = tuple(sorted(stage_durations.items()))
        # Memory usage placeholder – deterministic value set to zero.
        mem_bytes = 0
        # Event queue depth – placeholder value (network does not expose a queue).
        queue_depth = 0
        profile = PerformanceProfile(
            tick=tick,
            stage_durations_ms=sorted_items,
            memory_usage_bytes=mem_bytes,
            event_queue_depth=queue_depth,
        )
        self.profiles.append(profile)
        return profile
