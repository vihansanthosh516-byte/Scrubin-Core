"""Execution plan data structures for the deterministic tick engine.

The plan consists of an ordered list of ``ExecutionStage`` objects.  Each stage
wraps a callable that receives the ``Orchestrator`` instance and performs a
specific deterministic sub‑step (physiology, disease progression, PK/PD, …).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List


@dataclass(frozen=True)
class ExecutionStage:
    """A single deterministic stage in the tick pipeline.

    Attributes
    ----------
    name: Human‑readable identifier.
    handler: Callable[["Orchestrator"], None] – executes the stage.
    order: Integer used to sort stages into a deterministic sequence.
    """

    name: str
    handler: Callable[["Orchestrator"], None]
    order: int


@dataclass(frozen=True)
class ExecutionPlan:
    """Container for an ordered list of ``ExecutionStage`` objects.

    The ``stages`` list is guaranteed to be in deterministic order (sorted by
    ``order``).  The orchestrator simply iterates over the list each tick.
    """

    stages: List[ExecutionStage]
