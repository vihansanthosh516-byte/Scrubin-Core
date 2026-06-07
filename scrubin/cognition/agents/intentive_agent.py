"""Intentive agent – generates candidate intents.

For demonstration purposes the agent produces a single deterministic event per tick.
The event description embeds the ``agent_id`` to aid deterministic reconciliation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List

from scrubin.world.state import WorldState
from scrubin.core.events import TimelineEvent

from .base_agent import CognitiveAgent


@dataclass(frozen=True, slots=True)
class IntentiveAgent(CognitiveAgent):
    """Simple intent generation agent.

    The ``think`` method returns the current tick; ``emit`` creates a deterministic
    ``intent_generated`` event.
    """

    agent_id: str = field(default="intentive")
    role: str = field(default="intentive")
    priority: int = field(default=1)

    def perceive(self, world_state: WorldState) -> Any:
        # Provide a read‑only snapshot (the whole state is already immutable).
        return world_state

    def think(self, view: WorldState, seed: int, event_log: List[Any]) -> Any:
        # Deterministic output based solely on tick and seed.
        # No randomness – the seed is only recorded for completeness.
        return view.tick

    def emit(self, output: int) -> List[TimelineEvent]:
        # ``output`` is the tick number.
        return [TimelineEvent(tick=output, description=f"intent_generated:{self.agent_id}")]
