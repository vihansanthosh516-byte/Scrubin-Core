"""Deterministic communication primitives for surgical agents.

All messages are immutable dataclasses with a deterministic identifier. The
engine stores a tuple of pending messages and returns them in a deterministic
order (sorted by the message deterministic ID) each tick.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, replace
from typing import Tuple, List, Any

# ---------------------------------------------------------------------------
# Immutable message definition.
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Message:
    """Immutable communication payload.

    * ``sender_id`` – agent identifier of the origin.
    * ``receiver_id`` – target agent identifier (or "broadcast").
    * ``msg_type`` – symbolic type of the message (e.g., ``InstrumentRequest``).
    * ``content`` – free‑form string payload.
    * ``deterministic_id`` – SHA‑256 hash of the core fields for replay.
    """
    sender_id: str
    receiver_id: str
    msg_type: str
    content: str
    deterministic_id: str = field(init=False)

    def __post_init__(self) -> None:
        # Deterministic hash based on the immutable fields.
        combined = f"{self.sender_id}:{self.receiver_id}:{self.msg_type}:{self.content}"
        object.__setattr__(self, "deterministic_id", hashlib.sha256(combined.encode()).hexdigest())

# ---------------------------------------------------------------------------
# Deterministic communication engine – immutable container for pending msgs.
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class DeterministicCommunicationEngine:
    """Immutable engine that accumulates and propagates messages.

    The ``pending`` tuple holds messages awaiting delivery. ``send`` returns a new
    engine instance with the message appended. ``propagate`` returns messages
    sorted by ``deterministic_id`` and a fresh engine with an empty pending
    queue.
    """
    pending: Tuple[Message, ...] = field(default_factory=tuple)

    def send(self, message: Message) -> "DeterministicCommunicationEngine":
        return replace(self, pending=self.pending + (message,))

    def propagate(self) -> Tuple[List[Message], "DeterministicCommunicationEngine"]:
        ordered = sorted(self.pending, key=lambda m: m.deterministic_id)
        return ordered, replace(self, pending=tuple())
