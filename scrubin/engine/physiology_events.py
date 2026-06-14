"""Deterministic physiology event generator.

Generates deterministic physiology events for the current tick.
"""

from __future__ import annotations

from dataclasses import asdict, replace
from typing import List, Tuple

from scrubin.world.state import WorldState
from scrubin.models.types import ComplicationState
from scrubin.engine.decision_node import HiddenEffect
from scrubin.events.event import SurgicalEvent
from scrubin.events.event_types import PHYSIOLOGY_EVENT
from scrubin.core.events import TimelineEvent
from scrubin.engine.random import SimulationRNG

def _complication_deltas() -> dict:
    return {
        "hemorrhage": {"map": -10.0},
        "sepsis": {"spo2": -5.0},
    }

def generate_physiology_events(
    world: WorldState, rng: SimulationRNG
) -> Tuple[List[SurgicalEvent], List[TimelineEvent]]:
    events: List[SurgicalEvent] = []
    timeline: List[TimelineEvent] = []

    # 1️⃣ Apply active complication effects
    cardio = world.physiology.cardiovascular
    resp = world.physiology.respiratory
    for comp in world.complications.active:
        deltas = _complication_deltas().get(comp.id, {})
        if "map" in deltas:
            cardio = cardio.with_map(max(0.0, cardio.map + deltas["map"]))
        if "spo2" in deltas:
            resp = resp.with_spo2(max(0.0, resp.spo2 + deltas["spo2"]))
    phys_changed = cardio != world.physiology.cardiovascular or resp != world.physiology.respiratory

    # 2️⃣ Compensation logic (timeline side‑effects)
    if cardio.map < 70.0 and cardio.reserve > 0.0:
        if not cardio.compensation_active:
            timeline.append(TimelineEvent(tick=world.tick, description="compensation_started:cardiovascular"))
        new_hr = cardio.heart_rate + 5.0
        new_reserve = max(0.0, cardio.reserve - 0.1)
        active = new_reserve > 0.0
        cardio = cardio.with_heart_rate(new_hr).with_compensation(active, new_reserve)
        if not active:
            timeline.append(TimelineEvent(tick=world.tick, description="compensation_failed:cardiovascular"))
        phys_changed = True
    if resp.spo2 < 92.0 and resp.reserve > 0.0:
        if not resp.compensation_active:
            timeline.append(TimelineEvent(tick=world.tick, description="compensation_started:respiratory"))
        new_spo2 = min(100.0, resp.spo2 + 2.0)
        new_reserve = max(0.0, resp.reserve - 0.1)
        active = new_reserve > 0.0
        resp = resp.with_spo2(new_spo2).with_compensation(active, new_reserve)
        if not active:
            timeline.append(TimelineEvent(tick=world.tick, description="compensation_failed:respiratory"))
        phys_changed = True

    # 3️⃣ Hidden‑effect progression
    new_hidden: List[HiddenEffect] = []
    new_complications = world.complications
    for he in world.hidden_effects:
        if world.tick >= he.reveal_threshold:
            comp = ComplicationState(id=he.id, severity="moderate", onset_tick=world.tick)
            new_complications = new_complications.with_added(comp)
            timeline.append(TimelineEvent(tick=world.tick, description=f"occult_instability_detected:{he.id}"))
        else:
            new_hidden.append(he)
    hidden_changed = tuple(new_hidden) != world.hidden_effects
    comp_added_from_hidden = len(new_complications.active) != len(world.complications.active)

    # 4️⃣ Time‑pressure complication
    time_pressure_added = False
    if world.tick > 30:
        if not any(c.id == "time_pressure" for c in world.complications.active):
            comp = ComplicationState(id="time_pressure", severity="mild", onset_tick=world.tick)
            new_complications = new_complications.with_added(comp)
            timeline.append(TimelineEvent(tick=world.tick, description="time_pressure_active"))
            time_pressure_added = True

    # Assemble payload if any changes
    if phys_changed or time_pressure_added or comp_added_from_hidden or hidden_changed:
        payload: dict = {}
        if phys_changed:
            payload["physiology"] = {
                "cardiovascular": asdict(cardio),
                "respiratory": asdict(resp),
            }
        added_comps = []
        before_ids = {c.id for c in world.complications.active}
        for c in new_complications.active:
            if c.id not in before_ids:
                added_comps.append(c.to_dict())
        if added_comps:
            payload["complications"] = added_comps
        if hidden_changed:
            payload["hidden_effects"] = [asdict(he) for he in new_hidden]
        ev = SurgicalEvent(
            event_id=f"{world.tick}-phys-0",
            event_type=PHYSIOLOGY_EVENT,
            source="physiology_engine",
            tick=world.tick,
            priority=0,
            payload=payload,
        )
        events.append(ev)

    return events, timeline
