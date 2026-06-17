"""Deterministic interaction engine for Phase 8.3.

Transforms agent actions into interaction packets, resolves deterministic
conflicts, updates the environment and produces events.
"""

from __future__ import annotations

from typing import Tuple, List

from .models import (
    SimulationWorld,
    AgentAction,
    InteractionPacket,
    SimulationEvent,
)
from .environment_engine import EnvironmentEngine
from .event_engine import EventEngine


class InteractionEngine:
    """Core deterministic interaction processing.

    The workflow is:
    1. Convert ``AgentAction`` objects to ``InteractionPacket`` with a fixed
       priority order based on ``agent_id`` (lower id → higher priority).
    2. Resolve conflicts deterministically (instrument contention handled by
       ``EnvironmentEngine``).
    3. Apply the resolved packets to the environment.
    4. Generate deterministic events.
    """

    @staticmethod
    def _actions_to_packets(actions: Tuple[AgentAction, ...]) -> Tuple[InteractionPacket, ...]:
        packets: List[InteractionPacket] = []
        for act in actions:
            # Priority deterministic: lower agent_id gets higher priority.
            priority = act.agent_id
            packets.append(InteractionPacket(action=act, priority=priority))
        # Sort packets deterministically by priority.
        packets.sort(key=lambda p: p.priority)
        return tuple(packets)

    @staticmethod
    def process(world: SimulationWorld, actions: Tuple[AgentAction, ...]) -> Tuple[SimulationWorld, Tuple[InteractionPacket, ...], Tuple[SimulationEvent, ...]]:
        packets = InteractionEngine._actions_to_packets(actions)
        # Apply to environment (conflict resolution occurs inside).
        new_world = EnvironmentEngine.apply(world, packets)
        # Generate events based on the actions and environment changes.
        events = EventEngine.generate(new_world, actions)
        return new_world, packets, events
