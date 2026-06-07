"""Deterministic reconciliation engine for multi‑agent events.

The engine merges a list of ``TimelineEvent`` objects emitted by different agents
into a deterministic, conflict‑free sequence. The rules are:

1. **Deduplication** – identical ``(tick, description)`` pairs are collapsed.
2. **Priority resolution** – if two events share the same description but
   originate from different agents, the event from the higher‑priority agent
   (lower ``priority`` value) wins. The description format includes the agent id
   (e.g. ``"intent_generated:intentive"``) so the engine can extract the id.
3. **Tie‑break** – when priority is equal, a deterministic hash of the
   ``agent_id`` and ``description`` is used.

The engine is pure – it returns a new list without mutating inputs.
"""

from __future__ import annotations

import hashlib
from typing import List, Tuple

from scrubin.core.events import TimelineEvent
from scrubin.cognition.agents.base_agent import CognitiveAgent


class ReconciliationEngine:
    """Pure deterministic merger of agent‑generated events.

    ``reconcile`` returns a list of merged ``TimelineEvent`` objects sorted by
    tick (ascending) and then description.
    """

    @staticmethod
    def _agent_id_from_description(description: str) -> str:
        # Expected format: "<type>:<agent_id>" or may contain colon elsewhere.
        # We take the part after the last colon.
        if ":" in description:
            return description.split(":")[-1]
        return ""

    @staticmethod
    def _agent_priority(agent_id: str, agents: List[CognitiveAgent]) -> int:
        for a in agents:
            if a.agent_id == agent_id:
                return a.priority
        # Default low priority if unknown (should not happen).
        return 10**6

    def reconcile(self, events: List[TimelineEvent], agents: List[CognitiveAgent]) -> List[TimelineEvent]:
        # Preserve deterministic order: iterate over agents in sorted priority order.
        # Build a map of (tick, description) -> event selected.
        selected: dict[Tuple[int, str], TimelineEvent] = {}
        for event in events:
            key = (event.tick, event.description)
            if key not in selected:
                selected[key] = event
            else:
                # Conflict: same tick & description from different agents – resolve.
                existing = selected[key]
                # Extract agent ids
                aid_new = self._agent_id_from_description(event.description)
                aid_old = self._agent_id_from_description(existing.description)
                pr_new = self._agent_priority(aid_new, agents)
                pr_old = self._agent_priority(aid_old, agents)
                if pr_new < pr_old:
                    selected[key] = event
                elif pr_new == pr_old:
                    # deterministic tie‑break via hash
                    h_new = int(hashlib.sha256(event.description.encode()).hexdigest(), 16)
                    h_old = int(hashlib.sha256(existing.description.encode()).hexdigest(), 16)
                    if h_new < h_old:
                        selected[key] = event
        # Return sorted list for reproducibility.
        merged = list(selected.values())
        merged.sort(key=lambda ev: (ev.tick, ev.description))
        return merged
