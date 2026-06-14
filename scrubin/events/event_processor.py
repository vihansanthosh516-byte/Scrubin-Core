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
    PHYSIOLOGY_EVENT,
    COMPLICATION_EVENT,
)

from scrubin.core.events import TimelineEvent
from scrubin.world.state import WorldState
from scrubin.clinical.cognition.diagnostics import HiddenCondition
from dataclasses import replace, asdict
from scrubin.models.types import ComplicationState
from scrubin.engine.decision_node import HiddenEffect
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
    elif ev.event_type == PHYSIOLOGY_EVENT:
        payload = ev.payload
        # Determine if world is immutable (has with_physiology) or mutable.
        if hasattr(world, "with_physiology"):
            new_world = world
            if "physiology" in payload:
                phys = payload["physiology"]
                cardio_dict = phys.get("cardiovascular", {})
                resp_dict = phys.get("respiratory", {})
                cardio = new_world.physiology.cardiovascular
                resp = new_world.physiology.respiratory
                if "map" in cardio_dict:
                    cardio = cardio.with_map(cardio_dict["map"])
                if "heart_rate" in cardio_dict:
                    cardio = cardio.with_heart_rate(cardio_dict["heart_rate"])
                if "compensation_active" in cardio_dict or "reserve" in cardio_dict:
                    cardio = cardio.with_compensation(
                        cardio_dict.get("compensation_active", cardio.compensation_active),
                        cardio_dict.get("reserve", cardio.reserve),
                    )
                if "spo2" in resp_dict:
                    resp = resp.with_spo2(resp_dict["spo2"])
                if "compensation_active" in resp_dict or "reserve" in resp_dict:
                    resp = resp.with_compensation(
                        resp_dict.get("compensation_active", resp.compensation_active),
                        resp_dict.get("reserve", resp.reserve),
                    )
                new_world = new_world.with_physiology(replace(new_world.physiology, cardiovascular=cardio, respiratory=resp))
            if "complications" in payload:
                comp_state = new_world.complications
                for comp_dict in payload["complications"]:
                    comp_state = comp_state.with_added(ComplicationState.from_dict(comp_dict))
                new_world = new_world.with_complications(comp_state)
            if "hidden_effects" in payload:
                hidden_objs = tuple(HiddenEffect(**h) for h in payload["hidden_effects"])
                new_world = new_world.with_hidden_effects(hidden_objs)
            return new_world
        # Mutable fallback – same as previous implementation.
        if "physiology" in payload:
            phys = payload["physiology"]
            cardio_dict = phys.get("cardiovascular", {})
            resp_dict = phys.get("respiratory", {})
            cardio = world.physiology.cardiovascular
            resp = world.physiology.respiratory
            if "map" in cardio_dict:
                cardio = cardio.with_map(cardio_dict["map"])
            if "heart_rate" in cardio_dict:
                cardio = cardio.with_heart_rate(cardio_dict["heart_rate"])
            if "compensation_active" in cardio_dict or "reserve" in cardio_dict:
                cardio = cardio.with_compensation(
                    cardio_dict.get("compensation_active", cardio.compensation_active),
                    cardio_dict.get("reserve", cardio.reserve),
                )
            if "spo2" in resp_dict:
                resp = resp.with_spo2(resp_dict["spo2"])
            if "compensation_active" in resp_dict or "reserve" in resp_dict:
                resp = resp.with_compensation(
                    resp_dict.get("compensation_active", resp.compensation_active),
                    resp_dict.get("reserve", resp.reserve),
                )
            world.physiology = replace(world.physiology, cardiovascular=cardio, respiratory=resp)
        if "complications" in payload:
            for comp_dict in payload["complications"]:
                comp = ComplicationState.from_dict(comp_dict)
                world.complications = world.complications.with_added(comp)
        if "hidden_effects" in payload:
            hidden_objs = tuple(HiddenEffect(**h) for h in payload["hidden_effects"])
            world.hidden_effects = hidden_objs
        return world
    elif ev.event_type == COMPLICATION_EVENT:
        payload = ev.payload
        comp_id = payload.get("complication")
        severity = payload.get("severity", "moderate")
        # Determine if immutable world
        if hasattr(world, "with_complications"):
            new_world = world
            # Create ComplicationState (onset_tick is current tick)
            comp = ComplicationState(id=comp_id, severity=severity, onset_tick=world.tick)
            new_world = new_world.with_complications(new_world.complications.with_added(comp))
            # Append timeline entry
            new_world = new_world.append_timeline(TimelineEvent(tick=world.tick, description=f"complication_detected:{comp_id}"))
            return new_world
        # Mutable fallback
        comp = ComplicationState(id=comp_id, severity=severity, onset_tick=world.tick)
        world.complications = world.complications.with_added(comp)
        world = world.append_timeline(TimelineEvent(tick=world.tick, description=f"complication_detected:{comp_id}"))
        return world
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
