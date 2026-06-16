"""Deterministic immutable agent models for surgical team members.

Each agent is a frozen dataclass with a deterministic identifier calculated from its
static attributes and mutable state (workload, fatigue, current_task, etc.).
All state transitions use ``replace`` to preserve immutability.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, replace
from typing import Tuple, Optional, Any

# ---------------------------------------------------------------------------
# Base agent model – immutable snapshot of an operative actor.
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Agent:
    """Base immutable representation of a surgical team agent.

    Fields:
    * ``agent_id`` – unique identifier for the individual.
    * ``role`` – role string (e.g., "AttendingSurgeon").
    * ``current_task`` – identifier of the task currently being performed.
    * ``workload`` – cumulative work performed (deterministic count).
    * ``fatigue`` – float in [0,1] increasing with workload.
    * ``awareness`` – boolean indicating if the agent is actively engaged.
    * ``assigned_goal`` – optional goal identifier the agent is pursuing.
    * ``communication_queue`` – tuple of pending ``Message`` objects.
    * ``memory_snapshot`` – opaque deterministic snapshot of the agent's memory.
    * ``deterministic_id`` – SHA‑256 hash used for replay certification.
    """
    agent_id: str
    role: str
    current_task: Optional[str] = None
    workload: int = 0
    fatigue: float = 0.0
    awareness: bool = True
    assigned_goal: Optional[str] = None
    communication_queue: Tuple[Any, ...] = field(default_factory=tuple)
    memory_snapshot: Any = None
    deterministic_id: str = field(init=False)

    def __post_init__(self) -> None:
        # Deterministic ID based on immutable identity fields.
        parts = [self.agent_id, self.role]
        combined = "|".join(parts)
        object.__setattr__(self, "deterministic_id", hashlib.sha256(combined.encode()).hexdigest())

    # -------------------------------------------------------------------
    # Helper methods – return a new ``Agent`` with updated fields.
    # -------------------------------------------------------------------
    def with_task(self, task_id: Optional[str]) -> "Agent":
        return replace(self, current_task=task_id)

    def with_workload_increment(self, inc: int = 1) -> "Agent":
        new_workload = self.workload + inc
        # Simple linear fatigue increase; cap at 1.0.
        new_fatigue = min(1.0, self.fatigue + inc * 0.01)
        return replace(self, workload=new_workload, fatigue=new_fatigue)

    def enqueue_message(self, message: Any) -> "Agent":
        return replace(self, communication_queue=self.communication_queue + (message,))

    def dequeue_messages(self) -> Tuple[Tuple[Any, ...], "Agent"]:
        msgs = self.communication_queue
        return msgs, replace(self, communication_queue=tuple())

# ---------------------------------------------------------------------------
# Role‑specific subclasses – these provide convenient constructors.
# ---------------------------------------------------------------------------

# Role‑specific subclasses with a constant ``role`` field.
# ``init=False`` ensures the role is not required in the generated ``__init__``.

@dataclass(frozen=True, slots=True)
class AttendingSurgeon(Agent):
    role: str = field(default="AttendingSurgeon", init=False)

@dataclass(frozen=True, slots=True)
class ResidentSurgeon(Agent):
    role: str = field(default="ResidentSurgeon", init=False)

@dataclass(frozen=True, slots=True)
class ScrubNurse(Agent):
    role: str = field(default="ScrubNurse", init=False)

@dataclass(frozen=True, slots=True)
class CirculatingNurse(Agent):
    role: str = field(default="CirculatingNurse", init=False)

@dataclass(frozen=True, slots=True)
class Anesthesiologist(Agent):
    role: str = field(default="Anesthesiologist", init=False)

@dataclass(frozen=True, slots=True)
class SurgicalTechnician(Agent):
    role: str = field(default="SurgicalTechnician", init=False)
