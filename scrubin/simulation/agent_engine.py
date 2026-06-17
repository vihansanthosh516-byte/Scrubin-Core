"""Deterministic Agent Engine.

Agents are pure functions of the world snapshot.  For this implementation we
provide a minimal set of agents that emit *deterministic* (possibly empty)
``AgentAction`` objects based on the current ``SimulationWorld``.  No internal
state or randomness is introduced – each call to ``run`` returns a new tuple of
actions.
"""

from __future__ import annotations

from typing import Tuple

from .models import SimulationAgent, AgentAction, SimulationWorld


class AgentEngine:
    """Run deterministic agents and collect their actions.

    The engine holds a static, frozen tuple of ``SimulationAgent`` definitions.
    ``run`` receives the current ``SimulationWorld`` and returns a tuple of
    ``AgentAction`` objects produced by each agent.
    """

    # Define agents once – identifiers are deterministic.
    _agents: Tuple[SimulationAgent, ...] = (
        SimulationAgent(agent_id=1, agent_type="surgeon"),
        SimulationAgent(agent_id=2, agent_type="anesthesiologist"),
        SimulationAgent(agent_id=3, agent_type="nurse"),
        SimulationAgent(agent_id=4, agent_type="scrub_tech"),
        SimulationAgent(agent_id=5, agent_type="system_observer"),
    )

    @staticmethod
    def agents() -> Tuple[SimulationAgent, ...]:
        return AgentEngine._agents

    @staticmethod
    def run(world: SimulationWorld) -> Tuple[AgentAction, ...]:
        """Execute all agents on *world* and return deterministic actions.

        For this simplified implementation each agent emits a single action that
        depends only on immutable aspects of ``world`` (tick number and
        environment instrument availability).  The actions are intentionally
        trivial but fully deterministic.
        """
        actions: list[AgentAction] = []
        # Example deterministic behavior: each agent requests a distinct
        # instrument if available; otherwise no‑op.
        instruments = list(world.environment.available_instruments)
        for agent in AgentEngine._agents:
            if instruments:
                instr = instruments.pop(0)
                actions.append(
                    AgentAction(
                        agent_id=agent.agent_id,
                        action_type="request_instrument",
                        target=instr,
                    )
                )
            else:
                # No instrument left – agent does nothing this tick.
                actions.append(
                    AgentAction(
                        agent_id=agent.agent_id,
                        action_type="idle",
                        target="",
                    )
                )
        return tuple(actions)
