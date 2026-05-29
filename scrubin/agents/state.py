"""Immutable operative actor state model.

Defines the ``OperativeActor`` dataclass used by the multi‑agent runtime.
All fields are immutable; the engine creates new instances via ``replace``.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Tuple


@dataclass(frozen=True)
class OperativeActor:
    """Immutable representation of a single operative team member.

    * ``role`` – human‑readable role identifier (e.g. ``"primary_surgeon"``).
    * ``cognitive_load`` – workload factor, 0.0 (idle) to 1.0 (maxed).
    * ``situational_awareness`` – 0.0 (none) to 1.0 (full) – degrades with fatigue.
    * ``fatigue`` – accumulated fatigue, 0.0 to 1.0.
    * ``task_queue`` – ordered tuple of task identifiers pending for the actor.
    * ``communication_state`` – simple string describing the current communication
      status (``"clear"``, ``"pending"``, ``"blocked"``).
    * ``reliability`` – nominal reliability factor, 0.0 to 1.0.
    * ``response_latency`` – deterministic latency in ticks before the actor
      responds to a request.
    * ``procedural_context`` – identifier of the current procedural phase or
      activity.
    """

    role: str
    cognitive_load: float = 0.0
    situational_awareness: float = 1.0
    fatigue: float = 0.0
    task_queue: Tuple[str, ...] = field(default_factory=tuple)
    communication_state: str = "clear"
    reliability: float = 1.0
    response_latency: int = 0
    procedural_context: str = ""

    # ---------------------------------------------------------------------
    # Helper ``with_*`` methods – each returns a new immutable instance.
    # ---------------------------------------------------------------------
    def with_cognitive_load(self, load: float) -> "OperativeActor":
        return replace(self, cognitive_load=min(1.0, max(0.0, load)))

    def with_situational_awareness(self, awareness: float) -> "OperativeActor":
        return replace(self, situational_awareness=min(1.0, max(0.0, awareness)))

    def with_fatigue(self, fatigue: float) -> "OperativeActor":
        return replace(self, fatigue=min(1.0, max(0.0, fatigue)))

    def with_task_queue(self, queue: Tuple[str, ...]) -> "OperativeActor":
        return replace(self, task_queue=queue)

    def add_task(self, task_id: str) -> "OperativeActor":
        return replace(self, task_queue=self.task_queue + (task_id,))

    def with_communication_state(self, state: str) -> "OperativeActor":
        return replace(self, communication_state=state)

    def with_reliability(self, reliability: float) -> "OperativeActor":
        return replace(self, reliability=min(1.0, max(0.0, reliability)))

    def with_response_latency(self, latency: int) -> "OperativeActor":
        return replace(self, response_latency=max(0, latency))

    def with_procedural_context(self, context: str) -> "OperativeActor":
        return replace(self, procedural_context=context)


def default_actors() -> Tuple[OperativeActor, ...]:
    """Create a default ordered tuple of operative actors for a typical OR.

    The ordering is deterministic and can be used by the runtime engine to
    address actors by role.
    """
    roles = [
        "primary_surgeon",
        "assistant_surgeon",
        "anesthesiologist",
        "scrub_nurse",
        "circulating_nurse",
        "patient_autonomic",
    ]
    return tuple(OperativeActor(role=r) for r in roles)
