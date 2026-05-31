"""Stub ConsequenceMemory for deterministic testing.

Provides a minimal ``ConsequenceMemory`` data class with an ``overload_periods``
attribute used by the failure anticipation engine. All fields are immutable and
default to empty collections for deterministic behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple

@dataclass(frozen=True)
class ConsequenceMemory:
    """Simple stub with overload periods list."""
    overload_periods: Tuple[int, ...] = field(default_factory=tuple)
