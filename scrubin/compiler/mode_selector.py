"""Mode selector for ScrubIn Core.

Provides a deterministic enum that identifies which execution mode the
orchestrator should run in. The two supported modes are:

* ``SCIENTIFIC`` – full simulation, all cognition, auditing, replay hashing, etc.
* ``BENCHMARK`` – stripped‑down fast path used for benchmarks; only the core
  deterministic physics runs, no logging, no replay hooks, no heavy cognition.
"""

from __future__ import annotations

from enum import Enum


class ExecutionMode(Enum):
    SCIENTIFIC = "scientific"
    BENCHMARK = "benchmark"

    @classmethod
    def from_str(cls, mode_str: str) -> "ExecutionMode":
        """Parse a string into an ``ExecutionMode``.

        Raises ``ValueError`` for unsupported values.
        """
        normalized = mode_str.strip().lower()
        if normalized in ("scientific", "sci"):
            return cls.SCIENTIFIC
        if normalized in ("benchmark", "bench"):
            return cls.BENCHMARK
        raise ValueError(f"Invalid execution mode: {mode_str!r}")
