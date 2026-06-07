# Causal trace engine – deterministic reconstruction of event provenance.
"""
Provides a ``CausalTraceEngine`` that can answer "Why did this happen?"
by walking the timeline events generated during a run and building a chain of
causal nodes across cognitive phases.
"""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from typing import List, Any, Callable

# Local imports – the debug package already defines ``ReplayFrame`` etc.

@dataclass(frozen=True)
class CausalNode:
    """A single node in a causal chain.

    Attributes
    ----------
    phase: str
        The cognitive phase (e.g., "Intent", "Goal", "Arbitration", "Execution",
        "Reflection", "Learning").
    entity_id: str
        Identifier of the originating entity (often the agent ID extracted from the
        event description).
    input_state_hash: str
        Deterministic hash of the state *before* the event.
    output_state_hash: str
        Deterministic hash of the state *after* the event.
    """

    phase: str
    entity_id: str
    input_state_hash: str
    output_state_hash: str


@dataclass(frozen=True)
class CausalTrace:
    """Result of a causal trace lookup.

    Attributes
    ----------
    event_id: str
        Identifier of the target event (description string).
    tick: int
        Simulation tick the event occurred on.
    chain: List[CausalNode]
        Ordered list of causal nodes leading up to (and including) the target.
    """

    event_id: str
    tick: int
    chain: List[CausalNode]


class CausalTraceEngine:
    """Engine to construct causal traces for events in a deterministic run.

    The implementation is deliberately lightweight: it parses the ``description`` of
    timeline events, infers a phase, extracts the optional ``entity_id`` after a
    colon, and builds a chain of ``CausalNode`` objects linking state hashes before
    and after each event.
    """

    # Mapping from description prefix to readable phase name.
    _phase_map = {
        "intent_generated": "Intent",
        "goal_created": "Goal",
        "arbitration": "Arbitration",
        "execution": "Execution",
        "reflection": "Reflection",
        "learning": "Learning",
    }

    @staticmethod
    def _hash_dict(state: Any) -> str:
        """Deterministic hash for a dict‑like state snapshot.

        Uses a stable JSON representation with sorted keys and compact separators.
        """
        data = json.dumps(state, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(data.encode()).hexdigest()

    def _parse_event(self, description: str) -> tuple[str, str]:
        """Parse a timeline event description into phase and entity id.

        The description is expected to have the form ``"<prefix>:<entity>"``. If no
        colon is present, ``entity`` is returned as an empty string.
        """
        if ":" in description:
            prefix, entity = description.split(":", 1)
        else:
            prefix, entity = description, ""
        phase = self._phase_map.get(prefix, prefix.capitalize())
        return phase, entity

    def trace(self, artifact: Any, target_tick: int, target_description: str) -> CausalTrace:
        """Build a causal trace for ``target_description`` occurring at ``target_tick``.

        Parameters
        ----------
        artifact: ExecutionArtifact
            The run artifact containing a ``trajectory`` list of state snapshots.
        target_tick: int
            The tick index (0‑based) where the event of interest occurs.
        target_description: str
            The exact ``description`` string of the event to trace.

        Returns
        -------
        CausalTrace
            The assembled causal chain up to and including the target event.
        """
        # Retrieve the trajectory – list of state snapshots (dict‑like).
        trajectory = getattr(artifact, "trajectory", [])
        if not trajectory:
            raise ValueError("Artifact contains no trajectory data")
        if target_tick < 0 or target_tick >= len(trajectory):
            raise IndexError("target_tick out of range")

        # Pre‑compute hashes for each snapshot for efficiency.
        hashes = [self._hash_dict(state) for state in trajectory]

        chain: List[CausalNode] = []
        found = False
        # Iterate ticks up to the target tick inclusive.
        for idx in range(target_tick + 1):
            state = trajectory[idx]
            prev_hash = hashes[idx - 1] if idx > 0 else ""
            cur_hash = hashes[idx]
            # Timeline events may be stored under a ``timeline`` key.
            timeline_events = state.get("timeline", []) if isinstance(state, dict) else []
            for ev in timeline_events:
                # Each ``ev`` may be a dict or a ``scrubin.core.events.TimelineEvent``.
                if isinstance(ev, dict):
                    desc = ev.get("description", "")
                else:
                    # Fallback to attribute access.
                    desc = getattr(ev, "description", "")
                phase, entity = self._parse_event(desc)
                node = CausalNode(
                    phase=phase,
                    entity_id=entity,
                    input_state_hash=prev_hash,
                    output_state_hash=cur_hash,
                )
                chain.append(node)
                if idx == target_tick and desc == target_description:
                    found = True
                    # Stop processing further events after the target.
                    break
            if found:
                break
        # If the target event was not found we still return the collected chain.
        return CausalTrace(event_id=target_description, tick=target_tick, chain=chain)
