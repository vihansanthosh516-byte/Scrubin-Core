"""Reflective agent – evaluates past outcomes.

Generates a deterministic ``reflection`` event each tick.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List

from scrubin.world.state import WorldState
from scrubin.core.events import TimelineEvent

from .base_agent import CognitiveAgent


@dataclass(frozen=True, slots=True)
class ReflectiveAgent(CognitiveAgent):
    agent_id: str = field(default="reflective")
    role: str = field(default="reflective")
    priority: int = field(default=2)

    def perceive(self, world_state: WorldState) -> Any:
        return world_state

    def think(self, view: WorldState, seed: int, event_log: List[Any]) -> Any:
        # Simple deterministic function: return tick * 2
        return view.tick * 2

    def emit(self, output: int) -> List[TimelineEvent]:
        return [TimelineEvent(tick=output // 2, description=f"reflection:{self.agent_id}")]
