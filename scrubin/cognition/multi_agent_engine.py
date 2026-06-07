"""Deterministic multi‑agent cognition engine.

The engine orchestrates a set of :class:`~scrubin.cognition.agents.base_agent.CognitiveAgent`
instances. Execution order is deterministic based on ``priority`` and
``agent_id``. After each agent emits its events, the ``ReconciliationEngine``
merges them into a conflict‑free, deterministic list which is then appended to the
world's timeline.
"""

from __future__ import annotations

from typing import List, Tuple

from scrubin.world.state import WorldState
from scrubin.cognition.agents.base_agent import CognitiveAgent
from scrubin.cognition.reconciliation_engine import ReconciliationEngine
from scrubin.runtime.event_log import SessionEvent
from scrubin.core.events import TimelineEvent


class MultiAgentEngine:
    """Run a deterministic collection of agents for a single tick.

    The engine is pure – given the same ``WorldState``, ``seed`` and ``event_log``
    the output ``WorldState`` and merged events are always identical.
    """

    def __init__(self, agents: List[CognitiveAgent]):
        # Deterministic ordering – lower priority first, then by agent_id.
        self.agents = sorted(agents, key=lambda a: (a.priority, a.agent_id))
        self.reconciler = ReconciliationEngine()

    def run_step(self, world_state: WorldState, seed: int, event_log: List[SessionEvent]) -> Tuple[WorldState, List[TimelineEvent]]:
        # Collect events from each agent.
        raw_events: List[TimelineEvent] = []
        for agent in self.agents:
            # Per‑agent snapshot – world_state is immutable, safe to share.
            view = agent.perceive(world_state)
            output = agent.think(view, seed, event_log)
            evs = agent.emit(output)
            raw_events.extend(evs)
        # Deterministically merge events.
        merged_events = self.reconciler.reconcile(raw_events, self.agents)
        # Apply merged events to the world.
        new_world = world_state
        for ev in merged_events:
            new_world = new_world.append_timeline(ev)
        return new_world, merged_events
