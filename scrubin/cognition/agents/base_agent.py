"""Base class for deterministic cognitive agents.

Each agent is a frozen dataclass containing identifying metadata and must implement
three pure methods:

* ``perceive`` – produce a read‑only view of the world.
* ``think`` – deterministic reasoning based on the view, a seed and the
  global event log.
* ``emit`` – generate a list of ``TimelineEvent`` objects representing the
  agent's contribution for the current tick.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, List

from scrubin.world.state import WorldState
from scrubin.core.events import TimelineEvent
from scrubin.runtime.event_log import SessionEvent


@dataclass(frozen=True, slots=True)
class CognitiveAgent(ABC):
    """Immutable agent definition.

    Attributes
    ----------
    agent_id: str
        Unique identifier for the agent (used for deterministic tie‑breaks).
    role: str
        Human‑readable role name.
    priority: int
        Determines deterministic execution order – lower numbers run first.
    """

    agent_id: str
    role: str
    priority: int = field(default=0)

    @abstractmethod
    def perceive(self, world_state: WorldState) -> Any:
        """Create an immutable view of the world for this agent.

        The function **must not** mutate ``world_state``.
        """

    @abstractmethod
    def think(self, view: Any, seed: int, event_log: List[SessionEvent]) -> Any:
        """Pure deterministic reasoning.

        Returns an opaque ``output`` that will be consumed by ``emit``.
        """

    @abstractmethod
    def emit(self, output: Any) -> List[TimelineEvent]:
        """Translate ``output`` into timeline events.

        The returned events must be immutable ``TimelineEvent`` objects.
        """
