"""Deterministic simulation dataclasses for Phase 8.3.
All dataclasses are frozen, use slots, and expose a ``deterministic_hash``
computed from a tuple of their primitive fields.  Collections are immutable
``tuple`` objects and sorted where order matters.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from scrubin.learning.models import _det_hash
from typing import Tuple, Any


# ---------------------------------------------------------------------------
# Core simulation entities
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class SimulationAgent:
    """Immutable definition of a deterministic agent.

    ``agent_type`` identifies the role (e.g. "surgeon").  No internal mutable
    state is kept – agents are pure functions of the world snapshot.
    """

    agent_id: int
    agent_type: str
    # Additional static configuration can be added here.

    @property
    def deterministic_hash(self) -> int:
        return _det_hash(self)


@dataclass(frozen=True, slots=True)
class AgentAction:
    """Deterministic action emitted by an agent.

    ``action_type`` is a string identifier, ``target`` denotes the object of
    interaction (instrument name, patient region, etc.), and ``payload`` can be a
    primitive value – kept immutable.
    """

    agent_id: int
    action_type: str
    target: str
    payload: Any = None

    @property
    def deterministic_hash(self) -> int:
        return _det_hash(self)


@dataclass(frozen=True, slots=True)
class InteractionPacket:
    """Resolved packet ready for environment consumption."""

    action: AgentAction
    priority: int  # lower number = higher priority

    @property
    def deterministic_hash(self) -> int:
        return _det_hash(self)


@dataclass(frozen=True, slots=True)
class SimulationEvent:
    """Deterministic event generated during a tick."""

    event_type: str
    details: Tuple[Any, ...] = ()

    @property
    def deterministic_hash(self) -> int:
        return _det_hash(self)


@dataclass(frozen=True, slots=True)
class EnvironmentState:
    """Deterministic representation of the OR environment.

    ``available_instruments`` is a sorted tuple of instrument identifiers.
    ``sterile`` and ``lighting`` are simple booleans for deterministic
    conditions.
    """

    available_instruments: Tuple[str, ...] = ("scalpel", "retractor", "forceps")
    sterile: bool = True
    lighting: float = 1.0  # 0‑1 intensity

    @property
    def deterministic_hash(self) -> int:
        return _det_hash(self)


@dataclass(frozen=True, slots=True)
class SimulationWorld:
    """Top‑level simulation world – aggregates environment and physiology.

    ``environment`` holds OR state, ``physiology`` is the existing ``SystemsState``
    from the core simulation, and ``tick`` records the current tick number.
    """

    environment: EnvironmentState
    physiology: Any  # Expected to be a SystemsState instance.
    tick: int = 0

    @property
    def deterministic_hash(self) -> int:
        return _det_hash(self)


@dataclass(frozen=True, slots=True)
class SimulationSnapshot:
    """Immutable snapshot emitted after a full simulation tick."""

    world: SimulationWorld
    agents: Tuple[SimulationAgent, ...]
    events: Tuple[SimulationEvent, ...] = ()
    actions: Tuple[AgentAction, ...] = ()
    interaction_packets: Tuple[InteractionPacket, ...] = ()

    @property
    def deterministic_hash(self) -> int:
        return _det_hash(self)
