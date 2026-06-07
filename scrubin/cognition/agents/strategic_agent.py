"""Strategic agent – prioritizes goals.

For demo purposes it creates a deterministic ``strategic_decision`` event.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List

from scrubin.world.state import WorldState
from scrubin.core.events import TimelineEvent

from .base_agent import CognitiveAgent


@dataclass(frozen=True, slots=True)
class StrategicAgent(CognitiveAgent):
    agent_id: str = field(default="strategic")
    role: str = field(default="strategic")
    priority: int = field(default=3)

    def perceive(self, world_state: WorldState) -> Any:
        return world_state

    def think(self, view: WorldState, seed: int, event_log: List[Any]) -> Any:
        # Deterministic decision based on tick and seed.
        return (view.tick + seed) % 5

    def emit(self, output: int) -> List[TimelineEvent]:
        # Use the current tick from the world (reconstruct via view not passed).
        # For simplicity, embed output as tick.
        return [TimelineEvent(tick=output, description=f"strategic_decision:{self.agent_id}")]
