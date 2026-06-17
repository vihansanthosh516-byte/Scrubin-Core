"""Top‑level deterministic simulation manager for Phase 8.3.

The manager coordinates agents, interaction resolution, environment updates,
event generation and finally invokes the meta‑orchestration layer (Phase 8.2)
to validate the resulting world state.
"""

from __future__ import annotations

from typing import Tuple

from ..meta.meta_manager import MetaManager
from .agent_engine import AgentEngine
from .interaction_engine import InteractionEngine
from .models import (
    SimulationWorld,
    SimulationSnapshot,
    SimulationAgent,
    AgentAction,
    InteractionPacket,
    SimulationEvent,
)


class SimulationManager:
    """Deterministic driver for a single simulation tick.

    The ``tick`` method receives a ``SimulationWorld`` snapshot, runs all agents,
    resolves interactions, updates the environment, generates events, validates
    via the meta‑layer and returns a new ``SimulationSnapshot``.
    """

    @staticmethod
    def tick(world: SimulationWorld) -> SimulationSnapshot:
        # 1. Run agents – they observe the immutable world snapshot.
        agents: Tuple[SimulationAgent, ...] = AgentEngine.agents()
        actions: Tuple[AgentAction, ...] = AgentEngine.run(world)
        # 2. Interaction resolution and environment update.
        new_world, packets, events = InteractionEngine.process(world, actions)
        # 3. Meta‑layer validation (consistent with Phase 8.2).
        meta_snapshot = MetaManager.tick(new_world)
        # 4. Assemble deterministic simulation snapshot.
        return SimulationSnapshot(
            world=meta_snapshot.state,
            agents=agents,
            events=events,
            actions=actions,
            interaction_packets=packets,
        )
