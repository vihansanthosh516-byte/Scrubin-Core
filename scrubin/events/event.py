"""Immutable surgical event model.

All events are frozen dataclasses that compute a deterministic SHA‑256 hash of their
content (excluding the hash itself) for replay integrity checks.  The hash is
stored in the ``deterministic_hash`` field and is computed on construction.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List


def _stable_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively sort dictionaries/lists for deterministic JSON representation."""
    if isinstance(payload, dict):
        return {k: _stable_payload(payload[k]) for k in sorted(payload)}
    if isinstance(payload, list):
        return [_stable_payload(i) for i in payload]
    return payload


@dataclass(frozen=True)
class SurgicalEvent:
    """Immutable event used by the deterministic simulation engine.

    Attributes
    ----------
    event_id: str
        Unique identifier for the event (UUID4 string).
    event_type: str
        Identifier for the kind of event – see ``scrubin.events.event_types``.
    source: str
        Logical source of the event (e.g., ``"hidden_state_propagation"``).
    tick: int
        Simulation tick at which the event occurs.
    priority: int
        Deterministic priority ordering – lower numbers are processed first.
    payload: Dict[str, Any]
        Arbitrary JSON‑serialisable data describing the event.
    deterministic_hash: str
        SHA‑256 hash of the event content for replay verification.
    """

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = ""
    source: str = ""
    tick: int = 0
    priority: int = 0
    payload: Dict[str, Any] = field(default_factory=dict)
    deterministic_hash: str = field(init=False)

    def __post_init__(self):
        # Compute deterministic hash based on a stable JSON representation of the
        # event fields (excluding deterministic_hash itself).
        data = {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "source": self.source,
            "tick": self.tick,
            "priority": self.priority,
            "payload": _stable_payload(self.payload),
        }
        json_repr = json.dumps(data, sort_keys=True, separators=(",", ":"))
        hash_val = hashlib.sha256(json_repr.encode()).hexdigest()
        # Bypass frozen restriction using object.__setattr__
        object.__setattr__(self, "deterministic_hash", hash_val)
