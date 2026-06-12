"""Utility for converting user intents into deterministic SurgicalEvents.

The helper produces a fully deterministic ``SurgicalEvent`` – the ``event_id`` is
constructed from the simulation ``tick`` and the intent ``id`` (no random
UUID), guaranteeing identical hashes on replay.
"""

from __future__ import annotations

from typing import Any, Dict

from .event import SurgicalEvent
from .event_types import ACTION_EVENT
from scrubin.models.intents import ActionIntent


def create_action_event(tick: int, intent: ActionIntent, source: str = "user_action") -> SurgicalEvent:
    """Create a deterministic ``SurgicalEvent`` that wraps an ``ActionIntent``.

    The generated ``event_id`` is ``f"{tick}-{intent.id}"`` – this is stable for a
    given tick and intent identifier, avoiding any nondeterministic UUID.

    The event payload stores the full ``ActionIntent`` data (as a plain dict) so
    the existing :class:`ActionAuthority` can reconstruct the intent and perform
    its normal validation, duplicate‑check, and world‑mutation logic.
    """
    # Convert the dataclass to a plain dict – all fields are JSON‑serialisable.
    intent_dict: Dict[str, Any] = {
        "id": intent.id,
        "type": intent.type,
        "name": intent.name,
        "target": intent.target,
        "priority": intent.priority,
        "confidence": intent.confidence,
        "source": intent.source,
        "reasoning": intent.reasoning,
        "metadata": intent.metadata,
    }

    payload: Dict[str, Any] = {"intent": intent_dict}
    event_id = f"{tick}-{intent.id}"  # deterministic identifier
    return SurgicalEvent(
        event_id=event_id,
        event_type=ACTION_EVENT,
        source=source,
        tick=tick,
        priority=intent.priority,
        payload=payload,
    )
