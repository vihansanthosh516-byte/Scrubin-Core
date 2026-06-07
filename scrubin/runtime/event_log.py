"""Event log for deterministic replay.

Each session has an ordered list of immutable ``SessionEvent`` objects. The log is the
single source of truth for all state changes – a ``WorldState`` can always be rebuilt
from the latest snapshot plus the events that follow.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass(frozen=True, slots=True)
class SessionEvent:
    """Immutable event representing a single deterministic action.

    Attributes
    ----------
    session_id: str
        Identifier of the session this event belongs to.
    tick: int
        Logical simulation tick at which the event occurs.
    action_type: str
        High‑level action identifier (e.g. "monitor", "procedure").
    parameters: Dict[str, Any]
        JSON‑serialisable parameters for the action.
    seed: int
        RNG seed used for the deterministic engine (captured for reproducibility).
    """

    session_id: str
    tick: int
    action_type: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    seed: int = 0


class EventLog:
    """In‑memory deterministic event log.

    For production this would be backed by a persistent append‑only store (Redis list,
    Postgres, etc.). For the test suite a simple ``dict`` is sufficient.
    """

    def __init__(self) -> None:
        # Mapping ``session_id`` → ordered ``List[SessionEvent]``
        self._log: Dict[str, List[SessionEvent]] = {}

    def append(self, event: SessionEvent) -> None:
        self._log.setdefault(event.session_id, []).append(event)

    def get_events(self, session_id: str) -> List[SessionEvent]:
        return list(self._log.get(session_id, []))

    def clear(self) -> None:
        self._log.clear()
