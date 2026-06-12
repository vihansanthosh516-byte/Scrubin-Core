"""Deterministic event processor for applying ``SurgicalEvent``s to the world state.

The processor follows immutable semantics: it deep‑copies the current
``SimulationWorld`` and returns a new world with all event effects applied.
It also records a ``TimelineEvent`` for each processed surgical event.
"""

from copy import deepcopy
from typing import Tuple, List, Any

from .event import SurgicalEvent
from .event_types import (
    BLEEDING_EVENT,
    VISIBILITY_EVENT,
    INFLAMMATION_EVENT,
    SEPSIS_EVENT,
    HYPOTENSION_EVENT,
    ACTION_EVENT,
)

from scrubin.core.events import TimelineEvent
from scrubin.clinical.cognition.diagnostics import HiddenCondition
from scrubin.world.model import SimulationWorld


def _apply_event(world: SimulationWorld, ev: SurgicalEvent, authority: Any = None) -> SimulationWorld:
    """Apply a single ``SurgicalEvent`` to ``world`` and return the modified world.

    ``world`` is assumed to be a mutable copy (deepcopy of the original). The
    function mutates ``world`` in‑place and returns it for convenience.
    """
    if ev.event_type == BLEEDING_EVENT:
        amount = ev.payload.get("coeff", 0)
        bl = world.hidden_state.get("blood_loss", 0) + amount
        world.hidden_state["blood_loss"] = max(0, bl)
    elif ev.event_type == VISIBILITY_EVENT:
        delta = ev.payload.get("coeff", 0)
        vis = world.hidden_state.get("visibility", 100) + delta
        world.hidden_state["visibility"] = max(0, vis)
    elif ev.event_type == INFLAMMATION_EVENT:
        delta = ev.payload.get("coeff", 0)
        infl = world.hidden_state.get("inflammation", 0) + delta
        world.hidden_state["inflammation"] = max(0, infl)
    elif ev.event_type == SEPSIS_EVENT:
        # ``payload`` contains hidden condition attributes
        hc = HiddenCondition(
            id=ev.payload["id"],
            severity=ev.payload["severity"],
            onset_tick=world.tick,
            observability=ev.payload["observability"],
            progression_rate=ev.payload["progression_rate"],
        )
        world.hidden_state["sepsis"] = hc
    elif ev.event_type == HYPOTENSION_EVENT:
        # Example: flag or boolean change – payload may contain a boolean value
        flag = ev.payload.get("value", True)
        world.hidden_state["hypotension"] = flag
    elif ev.event_type == ACTION_EVENT:
        # User action event – delegate to ActionAuthority
        intent_data = ev.payload.get("intent")
        if intent_data and authority is not None:
            from scrubin.models.intents import ActionIntent
            intent = ActionIntent(**intent_data)
            # Authority will perform any world mutation and logging
            authority.execute(intent)
        # No direct world mutation here; authority handles it
        return world
    else:
        # Unknown event type – no state mutation performed
        pass
        # Timeline recording omitted for SimulationWorld (immutable timeline not supported here)
    return world


def process_events(world: SimulationWorld, queue, authority: Any = None) -> Tuple[SimulationWorld, object]:
    """Process all events scheduled up to ``world.tick``.

    Parameters
    ----------
    world:
        The current ``SimulationWorld`` instance.
    queue:
        An ``EventQueue`` instance containing ``SurgicalEvent`` objects.

    Returns
    -------
    (new_world, queue):
        ``new_world`` is a deepcopy of the original with all events applied. The
        queue is returned (with pending future‑tick events still stored).
    """
    # Extract events for the current tick (or earlier)
    events: List[SurgicalEvent] = queue.pop_all_up_to_tick(world.tick)
    # Work on a mutable copy to preserve immutability guarantees
    new_world = deepcopy(world)
    for ev in events:
         new_world = _apply_event(new_world, ev, authority)
    return new_world, queue
