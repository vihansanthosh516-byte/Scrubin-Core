"""Deterministic agent engine – per‑tick decision and communication handling.

All state updates are immutable: the engine returns a new tuple of agents,
new deterministic events, and an updated communication engine each tick.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Tuple, List, Dict, Any

from .models import Agent, AttendingSurgeon, ResidentSurgeon, ScrubNurse, CirculatingNurse, Anesthesiologist, SurgicalTechnician
from .communication import Message, DeterministicCommunicationEngine

# ---------------------------------------------------------------------------
# Simple deterministic task mapping per role.
# ---------------------------------------------------------------------------
_DEFAULT_TASKS = {
    "AttendingSurgeon": "lead_surgery",
    "ResidentSurgeon": "assist",
    "ScrubNurse": "hand_instrument",
    "CirculatingNurse": "manage_equipment",
    "Anesthesiologist": "maintain_anesthesia",
    "SurgicalTechnician": "prepare_implants",
}


class AgentEngine:
    """Engine that updates agents each simulation tick.

    The engine is immutable – ``tick`` returns a new ``AgentEngine`` state
    (via a fresh ``DeterministicCommunicationEngine``) together with the updated
    agents and a list of deterministic events.
    """

    def __init__(self, agents: Tuple[Agent, ...] = (), comm_engine: DeterministicCommunicationEngine = None) -> None:
        self.agents = agents
        self.comm_engine = comm_engine or DeterministicCommunicationEngine()

    # -------------------------------------------------------------------
    # Helper to select a deterministic task based on role.
    # -------------------------------------------------------------------
    @staticmethod
    def _task_for_role(role: str) -> str:
        return _DEFAULT_TASKS.get(role, "idle")

    # -------------------------------------------------------------------
    # Main per‑tick update.
    # -------------------------------------------------------------------
    def tick(self, world_snapshot: Any = None) -> Tuple[Tuple[Agent, ...], List[Dict], DeterministicCommunicationEngine]:
        """Execute a deterministic tick for all agents.

        ``world_snapshot`` is an opaque deterministic view of the world – agents may
        read but never modify it directly.
        Returns ``(new_agents, events, new_comm_engine)``.
        """
        # Deterministic ordering – sort agents by deterministic_id.
        ordered_agents = sorted(self.agents, key=lambda a: a.deterministic_id)
        new_agents: List[Agent] = []
        events: List[Dict] = []
        comm_engine = self.comm_engine
        # Clear any pending messages from previous tick (ignore them).
        _, comm_engine = comm_engine.propagate()

        for agent in ordered_agents:
            # Determine new state and events for this agent.
            if agent.current_task is None:
                # Assign a deterministic task based on role.
                task = _DEFAULT_TASKS.get(agent.role)
                if task:
                    events.append({
                        "type": "TaskAssigned",
                        "agent": agent.deterministic_id,
                        "task": task,
                    })
                    # Update agent with new task and increment workload.
                    new_agent = replace(agent, current_task=task, workload=agent.workload + 1)
                    # Scrub nurse sends an instrument request when taking its task.
                    if agent.role == "ScrubNurse":
                        msg = Message(
                            sender_id=agent.agent_id,
                            receiver_id="AttendingSurgeon",
                            msg_type="InstrumentRequest",
                            content="Requesting scalpel",
                        )
                        comm_engine = comm_engine.send(msg)
                        events.append({
                            "type": "MessageSent",
                            "agent": agent.deterministic_id,
                            "msg_type": "InstrumentRequest",
                        })
                else:
                    # No task defined for this role – remain idle.
                    new_agent = agent
                new_agents.append(new_agent)
            else:
                # Agent has an active task – complete it.
                events.append({
                    "type": "TaskCompleted",
                    "agent": agent.deterministic_id,
                    "task": agent.current_task,
                })
                # Clear the task and decrement workload.
                new_agent = replace(agent, current_task=None, workload=agent.workload - 1)
                if new_agent.workload < 0:
                    new_agent = replace(new_agent, workload=0)
                new_agents.append(new_agent)
        return tuple(new_agents), events, comm_engine
