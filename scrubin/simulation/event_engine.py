"""Deterministic event engine.

Generates a tuple of ``SimulationEvent`` objects based on the current world and
agent actions.  The logic is intentionally simple and fully deterministic.
"""

from __future__ import annotations

from typing import Tuple

from .models import SimulationWorld, AgentAction, SimulationEvent


class EventEngine:
    """Generate deterministic simulation events.

    Currently supports:
    * ``instrument_requested`` – emitted when an agent successfully requests an
      instrument.
    * ``idle`` – emitted for agents that perform the ``idle`` action.
    """

    @staticmethod
    def generate(world: SimulationWorld, actions: Tuple[AgentAction, ...]) -> Tuple[SimulationEvent, ...]:
        events: list[SimulationEvent] = []
        for act in actions:
            if act.action_type == "request_instrument":
                events.append(
                    SimulationEvent(event_type="instrument_requested", details=(act.agent_id, act.target))
                )
            elif act.action_type == "idle":
                events.append(
                    SimulationEvent(event_type="idle", details=(act.agent_id,))
                )
        # Sort events deterministically by event_type then details.
        events.sort(key=lambda e: (e.event_type, e.details))
        return tuple(events)
