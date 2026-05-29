"""Deterministic Physiologic Evolution Engine.

This engine updates the immutable ``WorldState`` on each simulation tick. It
incorporates:

* organ‑system compensation and de‑compensation,
* deterministic complication escalation (via ``ComplicationEngine``),
* hidden‑effect progression and manifestation,
* time‑pressure effects, and
* timeline event emission.

All state transitions are pure – a new ``WorldState`` is returned and the
original is left untouched, guaranteeing replay safety.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Dict, List, Tuple

from scrubin.world.state import (
    WorldState,
    PhysiologicalState,
    ProcedureState,
    ComplicationWorldState,
    TimelineEvent,
    CognitiveState,
    ScoringState,
    ResourceState,
)
from scrubin.engine.random import SimulationRNG
from scrubin.models.types import ComplicationState, ComplicationSeverity
from scrubin.engine.decision_node import HiddenEffect
from scrubin.agents.runtime_engine import MultiAgentRuntimeEngine
from scrubin.engine.systems_biology_engine import SystemsBiologyEngine

# ---------------------------------------------------------------------------
# Organ‑system state definitions (simplified for demonstration)
# ---------------------------------------------------------------------------

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CardiovascularState:
    map: float = 100.0  # mean arterial pressure
    heart_rate: float = 80.0
    compensation_active: bool = False
    reserve: float = 1.0  # abstract reserve for compensation
    failure_threshold: float = 50.0

    def with_map(self, new_map: float) -> "CardiovascularState":
        return replace(self, map=new_map)

    def with_heart_rate(self, new_hr: float) -> "CardiovascularState":
        return replace(self, heart_rate=new_hr)

    def with_compensation(self, active: bool, reserve: float) -> "CardiovascularState":
        return replace(self, compensation_active=active, reserve=reserve)


@dataclass(frozen=True)
class RespiratoryState:
    spo2: float = 98.0
    compensation_active: bool = False
    reserve: float = 1.0
    failure_threshold: float = 85.0

    def with_spo2(self, new_spo2: float) -> "RespiratoryState":
        return replace(self, spo2=new_spo2)

    def with_compensation(self, active: bool, reserve: float) -> "RespiratoryState":
        return replace(self, compensation_active=active, reserve=reserve)

# Additional organ states can be added similarly (perfusional, neurologic, renal, ...)


# ---------------------------------------------------------------------------
# Main Evolution Engine
# ---------------------------------------------------------------------------

class PhysiologicEvolutionEngine:
    """Deterministic engine that evolves the world physiologically each tick.

    The engine is deliberately pure – it never mutates its inputs.  All
    side‑effects (new complications, timeline events) are encoded in the returned
    ``WorldState``.
    """

    def __init__(self, rng: SimulationRNG):
        self.rng = rng
        # Simple deterministic mapping from complication id to progression delta
        self.complication_deltas: Dict[str, Dict[str, float]] = {
            "hemorrhage": {"map": -10.0},
            "sepsis": {"spo2": -5.0},
        }
        self.biology_engine = SystemsBiologyEngine(rng)
        self.agent_runtime_engine = MultiAgentRuntimeEngine(rng)
            "hemorrhage": {"map": -10.0},
            "sepsis": {"spo2": -5.0},
        }

    def _apply_complications(self, world: WorldState) -> WorldState:
        """Apply active complication effects to organ systems.

        Complication effects are defined in ``self.complication_deltas``.  The
        example mappings are intentionally simple but deterministic.
        """
        cardio = world.physiology.cardiovascular
        resp = world.physiology.respiratory
        for comp in world.complications.active:
            deltas = self.complication_deltas.get(comp.id, {})
            if "map" in deltas:
                new_map = max(0.0, cardio.map + deltas["map"])
                cardio = cardio.with_map(new_map)
            if "spo2" in deltas:
                new_spo2 = max(0.0, resp.spo2 + deltas["spo2"])
                resp = resp.with_spo2(new_spo2)
        return world.with_physiology(
            replace(world.physiology, cardiovascular=cardio, respiratory=resp)
        )

    def _compensate(self, world: WorldState) -> WorldState:
        """Apply deterministic compensation mechanisms.

        * Tachycardia compensates for low MAP.
        * Increased respiratory rate (simulated as higher ``spo2``) compensates for
          low oxygen delivery.
        Compensation consumes a reserve; when the reserve reaches 0 the
        mechanism fails and a ``compensation_failed`` event is emitted.
        """
        cardio = world.physiology.cardiovascular
        resp = world.physiology.respiratory
        events: List[TimelineEvent] = []

        # MAP compensation via tachycardia
        if cardio.map < 70.0 and cardio.reserve > 0.0:
            # Activate compensation if not already active
            if not cardio.compensation_active:
                events.append(TimelineEvent(tick=world.tick, description="compensation_started:cardiovascular"))
            # Increase heart rate modestly
            new_hr = cardio.heart_rate + 5.0
            new_reserve = max(0.0, cardio.reserve - 0.1)
            active = new_reserve > 0.0
            cardio = cardio.with_heart_rate(new_hr).with_compensation(active, new_reserve)
            if not active:
                events.append(TimelineEvent(tick=world.tick, description="compensation_failed:cardiovascular"))

        # SpO2 compensation via respiratory effort (placeholder)
        if resp.spo2 < 92.0 and resp.reserve > 0.0:
            if not resp.compensation_active:
                events.append(TimelineEvent(tick=world.tick, description="compensation_started:respiratory"))
            # Slightly improve spo2
            new_spo2 = min(100.0, resp.spo2 + 2.0)
            new_reserve = max(0.0, resp.reserve - 0.1)
            active = new_reserve > 0.0
            resp = resp.with_spo2(new_spo2).with_compensation(active, new_reserve)
            if not active:
                events.append(TimelineEvent(tick=world.tick, description="compensation_failed:respiratory"))
        # Apply any generated events to the timeline
        new_world = world.with_physiology(
            replace(world.physiology, cardiovascular=cardio, respiratory=resp)
        )
        for ev in events:
            new_world = new_world.append_timeline(ev)
        return new_world

    def _progress_hidden_effects(self, world: WorldState) -> WorldState:
        """Progress hidden effects and manifest them as complications when due.
        """
        new_hidden: List[HiddenEffect] = []
        new_complications = world.complications
        events: List[TimelineEvent] = []
        for he in world.hidden_effects:
            # Simple deterministic progression: advance a tick counter implicitly via world.tick.
            # When the current tick reaches the reveal threshold, manifest the effect.
            if world.tick >= he.reveal_threshold:
                # Manifest as a complication (use the hidden effect id as complication id).
                comp = ComplicationState(id=he.id, severity="moderate", onset_tick=world.tick)
                new_complications = new_complications.with_added(comp)
                events.append(TimelineEvent(tick=world.tick, description=f"occult_instability_detected:{he.id}"))
            else:
                new_hidden.append(he)
        # Preserve any hidden effects that have not yet manifested.
        new_world = world.with_hidden_effects(tuple(new_hidden)).with_complications(new_complications)
        for ev in events:
            new_world = new_world.append_timeline(ev)
        return new_world

    def _apply_time_pressure(self, world: WorldState) -> WorldState:
        """Simple time‑pressure model – increase instability with prolonged ticks.

        If the tick count exceeds a hard‑coded threshold (e.g., 30), we add a low‑
        severity ``time_pressure`` complication.
        """
        if world.tick > 30:
            comp = ComplicationState(id="time_pressure", severity="mild", onset_tick=world.tick)
            new_comp = world.complications.with_added(comp)
            ev = TimelineEvent(tick=world.tick, description="time_pressure_active")
            return world.with_complications(new_comp).append_timeline(ev)
        return world

    def evolve(self, world: WorldState) -> WorldState:
        """Advance the world by one deterministic physiologic tick.

        The order of operations mirrors typical physiologic cascades:
        1. Apply active complication effects.
        2. Apply compensatory mechanisms.
        3. Progress hidden effects.
        4. Apply time‑pressure penalties.
        5. Increment the tick counter.
        """
        # 1️⃣ Complication impact
        world = self._apply_complications(world)
        # 2️⃣ Compensation
        world = self._compensate(world)
        # 3️⃣ Hidden effect progression
        world = self._progress_hidden_effects(world)
        # 4️⃣ Time pressure
        world = self._apply_time_pressure(world)
        # 5️⃣ Biological subsystem evolution (deterministic)
        world = self.biology_engine.evolve(world)
        # 6️⃣ Multi‑agent runtime evolution (deterministic)
        world = self.agent_runtime_engine.evolve(world)
        # 7️⃣ Advance tick (deterministic)
        world = world.tick_forward()
        return world
