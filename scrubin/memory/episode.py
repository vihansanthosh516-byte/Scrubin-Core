"""Episodic memory data structures.

Immutable data classes representing a single replayable episode of a simulation tick.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple, Any


@dataclass(frozen=True)
class Observation:
    """Immutable observation captured during an episode.

    name: Name of the measured quantity (e.g., "BloodPressure").
    value: Measured value – can be any JSON‑serialisable type.
    tick: Simulation tick at which the observation was recorded.
    """

    name: str
    value: Any
    tick: int


@dataclass(frozen=True)
class ActionSummary:
    """Summary of an action taken during the episode.

    name: Action name (e.g., "Clamp Vessel").
    agent: Identifier of the source executing the action.
    tick: Simulation tick of the action.
    """

    name: str
    agent: str
    tick: int


@dataclass(frozen=True)
class ConsequenceSummary:
    """Summary of a consequence (e.g., complication) generated.

    name: Description of the consequence (e.g., "Bleeding").
    severity: Numeric severity weight – may be ``None`` if not applicable.
    tick: Simulation tick when the consequence occurred.
    """

    name: str
    severity: float | None
    tick: int


@dataclass(frozen=True)
class Episode:
    """Immutable replayable episode.

    The episode aggregates all deterministic information for a single tick.
    It is never mutated after creation – episodes are appended to the store.
    """

    id: str
    tick: int
    phase: str
    participants: Tuple[str, ...]
    observations: Tuple[Observation, ...]
    actions: Tuple[ActionSummary, ...]
    consequences: Tuple[ConsequenceSummary, ...]
    outcome: str
    importance: float
    event_ids: Tuple[str, ...]
    replay_hash: str
