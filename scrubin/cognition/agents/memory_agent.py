"""Memory agent – interacts with the knowledge graph.

Creates a deterministic ``memory_update`` event each tick.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List

from scrubin.world.state import WorldState
from scrubin.core.events import TimelineEvent

from .base_agent import CognitiveAgent


@dataclass(frozen=True, slots=True)
class MemoryAgent(CognitiveAgent):
    agent_id: str = field(default="memory")
    role: str = field(default="memory")
    priority: int = field(default=4)

    def perceive(self, world_state: WorldState) -> Any:
        return world_state

    def think(self, view: WorldState, seed: int, event_log: List[Any]) -> Any:
        # Deterministic “knowledge” based on tick and seed.
        return (view.tick + seed) * 3

    def emit(self, output: int) -> List[TimelineEvent]:
        # Use the output value as tick (deterministic).
        return [TimelineEvent(tick=output, description=f"memory_update:{self.agent_id}")]
