"""Scrubin‑Core deterministic engine – Python port of the ScrubIn TypeScript engine.

Reproduces the simulation semantics and JSON contract of the original
``server/engine`` TypeScript implementation:
  - DeterministicRNG (xorshift32, bit‑exact with the JS version)
  - Vitals / Complication / Decision engines
  - SimulationOrchestrator + SessionManager + SessionState

All field names mirror the lowercase JSON contract consumed by the React UI
(snake_case appears at the API boundary; the orchestrator/session objects use
camelCase internally to match the TS source closely).
"""

from __future__ import annotations

import math
import threading
import time
from typing import Optional

from scrubin_core_procedures import (
    DEFAULT_VITALS,
    VITAL_RANGES,
    clamp_vitals,
    COMPLICATION_VITAL_EFFECTS,
    ARCHETYPE_COMPLICATION_MAP,
    ARCHETYPE_PROMPTS,
    ARCHETYPE_INTERVENTIONS,
    ESCALATION_LABELS,
    list_procedures,
    get_procedure,
    procedure_exists,
)


# ─────────────────────────────────────────────────────────────────────────────
# Deterministic RNG – bit‑exact port of the JS xorshift32
# ─────────────────────────────────────────────────────────────────────────────

_INT32_MASK = 0xFFFFFFFF


def _int32(x: int) -> int:
    """JS ``x | 0`` – two's complement 32‑bit signed."""
    x &= _INT32_MASK
    if x >= 0x80000000:
        x -= 0x100000000
    return x


def _uint32(x: int) -> int:
    """JS ``x >>> 0`` – unsigned 32‑bit."""
    return x & _INT32_MASK


class DeterministicRNG:
    __slots__ = ("state",)

    def __init__(self, seed: int):
        self.state = _int32(seed)
        if self.state == 0:
            self.state = 1

    def next(self) -> float:
        s = self.state
        s = _int32(_uint32(s << 13))
        s = _int32(s >> 17)            # arithmetic shift right on signed value
        s = _int32(_uint32(s << 5))
        self.state = _int32(s)
        return _uint32(self.state) / 4294967296.0

    def next_int(self, mn: int, mx: int) -> int:
        return math.floor(self.next() * (mx - mn + 1)) + mn

    def next_float(self, mn: float, mx: float) -> float:
        return self.next() * (mx - mn) + mn

    def pick(self, arr):
        return arr[math.floor(self.next() * len(arr))]

    def weighted_pick(self, weights: dict):
        entries = list(weights.items())
        total = sum(w for _k, w in entries)
        r = self.next() * total
        for k, w in entries:
            r -= w
            if r <= 0:
                return k
        return entries[-1][0]

    def clone(self) -> "DeterministicRNG":
        c = DeterministicRNG.__new__(DeterministicRNG)
        c.state = self.state
        return c


# ─────────────────────────────────────────────────────────────────────────────
# Vitals engine + Complication engine
# ─────────────────────────────────────────────────────────────────────────────

class VitalsEngine:
    def __init__(self, initial_vitals: dict, rng: DeterministicRNG, risk_profile: dict):
        self.vitals = dict(initial_vitals)
        self.rng = rng
        self.risk_profile = risk_profile
        self.pending_effects: list[dict] = []  # [{ tick, effect: {key:val} }]

    def snapshot(self) -> dict:
        return dict(self.vitals)

    def apply_complication(self, comp: str, severity: float = 1.0) -> None:
        effects = COMPLICATION_VITAL_EFFECTS.get(comp)
        if not effects:
            return
        for key, val in effects.items():
            if val is not None:
                self.vitals[key] += val * severity
        self.vitals = clamp_vitals(self.vitals)

    def apply_intervention(self, effect: dict, spread_over_ticks: int = 3, current_tick: int = 0) -> None:
        per_tick: dict = {}
        for key, val in effect.items():
            if val is not None:
                per_tick[key] = val / spread_over_ticks
        for i in range(1, spread_over_ticks + 1):
            self.pending_effects.append({"tick": current_tick + i, "effect": dict(per_tick)})

    def tick(self, tick: int) -> dict:
        recovery = self.risk_profile["recovery_speed"]
        for key, target in DEFAULT_VITALS.items():
            current = self.vitals[key]
            drift = self.rng.next_float(-0.3, 0.3)
            self.vitals[key] += (target - current) * 0.02 * recovery + drift
        due = [e for e in self.pending_effects if e["tick"] <= tick]
        for entry in due:
            for key, val in entry["effect"].items():
                if val is not None:
                    self.vitals[key] += val
        self.pending_effects = [e for e in self.pending_effects if e["tick"] > tick]
        self.vitals = clamp_vitals(self.vitals)
        return self.snapshot()


class ComplicationEngine:
    def __init__(self, rng: DeterministicRNG, weights: dict, allowed: list, risk_profile: dict):
        self.rng = rng
        self.allowed = list(allowed)
        self.weights = self._normalize_weights(weights)
        self.risk_profile = risk_profile
        self.active: Optional[str] = None
        self.active_since_tick = -1

    def _normalize_weights(self, w: dict) -> dict:
        filtered: dict = {}
        total = 0
        for key in self.allowed:
            val = w.get(key, 0)
            if val and val > 0:
                filtered[key] = val
                total += val
        if total == 0:
            return filtered
        for key in list(filtered.keys()):
            filtered[key] = filtered[key] / total
        return filtered

    def get_active(self) -> Optional[str]:
        return self.active

    def resolve(self) -> None:
        self.active = None
        self.active_since_tick = -1

    def tick(self, tick: int, escalation_phase: str) -> Optional[str]:
        if self.active:
            return None
        chance = self._spawn_chance(escalation_phase)
        if self.rng.next() > chance:
            return None
        keys = list(self.weights.keys())
        if not keys:
            return None
        comp = self.rng.weighted_pick(self.weights)
        self.active = comp
        self.active_since_tick = tick
        return comp

    def _spawn_chance(self, phase: str) -> float:
        base = self.risk_profile["base_complication_chance"]
        return {
            "stable_workup": base * 0.2,
            "complication_risk": base * 0.6,
            "active_complication": base * 1.0,
            "crisis_management": base * 1.4,
            "recovery_or_failure": base * 0.3,
        }.get(phase, base)


# ─────────────────────────────────────────────────────────────────────────────
# Decision engine
# ─────────────────────────────────────────────────────────────────────────────

class DecisionEngine:
    def __init__(self, rng: DeterministicRNG, procedure: dict):
        self.rng = rng
        self.procedure = procedure
        self.decision_counter = 0

    def generate_decision(self, tick, vitals, escalation_phase, active_complication, procedure_phase) -> dict:
        archetypes = self.procedure["decisionArchetypes"]
        if active_complication:
            archetype = self._pick_archetype_for_complication(archetypes, active_complication)
        else:
            archetype = self.rng.pick(archetypes)

        prompt_data = ARCHETYPE_PROMPTS[archetype]
        interventions = ARCHETYPE_INTERVENTIONS[archetype]

        options = []
        for iv in interventions:
            options.append({
                "id": iv["id"],
                "label": iv["label"],
                "archetype": archetype,
                "correctForComplications": list(iv["treats"]),
                "effectOnVitals": dict(iv["vitalsEffect"]),
                "riskIfWrong": dict(iv["riskIfWrong"]),
                "feedback": {"correct": iv["correctFeedback"], "wrong": iv["wrongFeedback"]},
            })

        if len(options) != 4:
            raise RuntimeError(f"DecisionEngine: archetype {archetype} produced {len(options)} options, expected exactly 4")

        self._shuffle(options)
        urgency = self._compute_urgency(vitals, active_complication, escalation_phase)
        self.decision_counter += 1
        decision_id = f"decision_{self.procedure['id']}_{self.decision_counter}"

        return {
            "id": decision_id,
            "tick": tick,
            "phase": escalation_phase,
            "phaseLabel": ESCALATION_LABELS[escalation_phase],
            "procedurePhase": procedure_phase,
            "archetype": archetype,
            "prompt": self._contextualize_prompt(prompt_data["prompt"], vitals, active_complication),
            "context": prompt_data["context"],
            "options": options,
            "urgency": urgency,
        }

    def evaluate_decision(self, decision, option_id, vitals, active_complication) -> dict:
        option = next((o for o in decision["options"] if o["id"] == option_id), None)
        if option is None:
            return {
                "wasCorrect": False,
                "complicationTriggered": None,
                "vitalsEffect": {},
                "feedback": "Invalid option selected.",
                "scoreDelta": -5,
            }

        was_correct = False
        if active_complication:
            was_correct = active_complication in option["correctForComplications"]
        else:
            risk = option["riskIfWrong"]
            is_low_risk = all((v is None or abs(v) < 8) for v in risk.values())
            was_correct = is_low_risk

        if was_correct:
            return {
                "wasCorrect": True,
                "complicationTriggered": None,
                "vitalsEffect": dict(option["effectOnVitals"]),
                "feedback": option["feedback"]["correct"],
                "scoreDelta": self._compute_score_delta(decision["urgency"], True),
            }

        possible = ARCHETYPE_COMPLICATION_MAP[option["archetype"]]
        trigger = None
        if not active_complication and self.rng.next() < 0.4:
            trigger = self.rng.pick(possible)
        return {
            "wasCorrect": False,
            "complicationTriggered": trigger,
            "vitalsEffect": dict(option["riskIfWrong"]),
            "feedback": option["feedback"]["wrong"],
            "scoreDelta": self._compute_score_delta(decision["urgency"], False),
        }

    def _pick_archetype_for_complication(self, archetypes, comp) -> str:
        matching = [a for a in archetypes if comp in ARCHETYPE_COMPLICATION_MAP[a]]
        if matching:
            return self.rng.pick(matching)
        return self.rng.pick(archetypes)

    def _compute_urgency(self, vitals, comp, phase) -> str:
        if phase == "crisis_management":
            return "critical"
        if comp:
            return "high"
        if vitals["spo2"] < 90 or vitals["heart_rate"] > 120 or vitals["bp_systolic"] < 85:
            return "high"
        if vitals["spo2"] < 94 or vitals["heart_rate"] > 100 or vitals["bp_systolic"] < 100:
            return "medium"
        return "low"

    def _compute_score_delta(self, urgency: str, correct: bool) -> int:
        base = 10 if correct else -5
        multiplier = {"critical": 3, "high": 2, "medium": 1.5, "low": 1}.get(urgency, 1)
        return int(round(base * multiplier))

    def _contextualize_prompt(self, prompt: str, vitals, comp) -> str:
        if comp:
            return f"⚠️ {comp.replace('_', ' ').upper()} — {prompt}"
        if vitals["spo2"] < 90:
            return f"📉 SpO2: {vitals['spo2']}% — {prompt}"
        if vitals["heart_rate"] > 120:
            return f"💓 HR: {vitals['heart_rate']} — {prompt}"
        if vitals["bp_systolic"] < 90:
            return f"🩸 BP: {vitals['bp_systolic']}/{vitals['bp_diastolic']} — {prompt}"
        return prompt

    def _shuffle(self, arr) -> None:
        for i in range(len(arr) - 1, 0, -1):
            j = math.floor(self.rng.next() * (i + 1))
            arr[i], arr[j] = arr[j], arr[i]


# ─────────────────────────────────────────────────────────────────────────────
# Orchestrator
# ─────────────────────────────────────────────────────────────────────────────

class SimulationOrchestrator:
    def __init__(self, seed: int, procedure_id: str):
        self.rng = DeterministicRNG(seed)
        self.procedure = get_procedure(procedure_id)
        if self.procedure is None:
            raise RuntimeError(f"Unknown procedure: {procedure_id}")

        vitals = dict(self.procedure["patient"]["baselineVitals"])
        vitals.update(self.procedure["initialState"]["vitals_override"])
        self.vitals_engine = VitalsEngine(vitals, self.rng.clone(), self.procedure["initialState"]["riskProfile"])
        self.comp_engine = ComplicationEngine(
            self.rng.clone(),
            self.procedure["complicationWeights"],
            self.procedure["allowedComplications"],
            self.procedure["initialState"]["riskProfile"],
        )
        self.decision_engine = DecisionEngine(self.rng.clone(), self.procedure)

        self._tick = 0
        self.score = 0
        self.max_score = 0
        self.completed = False
        self.pending_decision: Optional[dict] = None
        self.pending_decision_state: Optional[dict] = None
        self.decision_history: list[dict] = []
        self.active_complication: Optional[str] = None
        self.events: list[str] = []

    def next(self) -> dict:
        if self.completed:
            return self._build_result(None)
        if self.pending_decision_state and not self.pending_decision_state["resolved"]:
            raise RuntimeError("Cannot advance tick without decision")

        self._tick += 1
        self.events = []

        vitals_before = self.vitals_engine.snapshot()
        escalation = self._escalation_phase()

        spawned = self.comp_engine.tick(self._tick, escalation)
        if spawned:
            self.active_complication = spawned
            self.vitals_engine.apply_complication(spawned, self._complication_severity(escalation))
            self.events.append(f"Complication: {spawned.replace('_', ' ')}")

        if not spawned and self.active_complication and not self.comp_engine.get_active():
            self.active_complication = None

        vitals_after_complication = self.vitals_engine.snapshot()
        procedure_phase = self._procedure_phase()
        self.pending_decision = self.decision_engine.generate_decision(
            self._tick, vitals_after_complication, escalation, self.active_complication, procedure_phase
        )
        self.pending_decision_state = {"tick": self._tick, "decisionId": self.pending_decision["id"], "resolved": False}

        vitals_after = self.vitals_engine.tick(self._tick)
        self.max_score += 10
        return self._build_result(None, vitals_before, vitals_after)

    def submit_decision(self, decision_id: str, option_id: str) -> dict:
        if not self.pending_decision or self.pending_decision["id"] != decision_id:
            raise RuntimeError("Invalid decision ID or no pending decision")
        if not self.pending_decision_state or self.pending_decision_state["resolved"]:
            raise RuntimeError("No pending decision to resolve")

        vitals_before = self.vitals_engine.snapshot()
        eval_ = self.decision_engine.evaluate_decision(self.pending_decision, option_id, vitals_before, self.active_complication)
        self.score += eval_["scoreDelta"]

        if eval_["wasCorrect"]:
            self.vitals_engine.apply_intervention(eval_["vitalsEffect"], 3, self._tick)
            self.events.append(eval_["feedback"])
            if self.active_complication:
                self.comp_engine.resolve()
                self.active_complication = None
                self.events.append("Complication resolved")
        else:
            self.vitals_engine.apply_intervention(eval_["vitalsEffect"], 1, self._tick)
            if eval_["complicationTriggered"] and not self.active_complication:
                self.active_complication = eval_["complicationTriggered"]
                self.vitals_engine.apply_complication(eval_["complicationTriggered"], 0.7)
                self.events.append(f"Wrong decision triggered: {eval_['complicationTriggered'].replace('_', ' ')}")
            self.events.append(eval_["feedback"])

        result = {
            "decisionId": decision_id,
            "optionId": option_id,
            "wasCorrect": eval_["wasCorrect"],
            "complicationTriggered": eval_["complicationTriggered"],
            "vitalsBefore": vitals_before,
            "vitalsAfter": self.vitals_engine.snapshot(),
            "feedback": eval_["feedback"],
            "scoreDelta": eval_["scoreDelta"],
        }
        self.decision_history.append(result)
        self.pending_decision = None
        self.pending_decision_state = {**self.pending_decision_state, "resolved": True}

        if self._tick >= self.procedure["totalTicks"]:
            self.completed = True
            self.events.append("Simulation complete")

        return self._build_result(result, result["vitalsBefore"], result["vitalsAfter"])

    def _build_result(self, decision_result, vitals_before=None, vitals_after=None) -> dict:
        if vitals_before is None:
            vitals_before = self.vitals_engine.snapshot()
        if vitals_after is None:
            vitals_after = self.vitals_engine.snapshot()
        return {
            "tick": self._tick,
            "vitalsBefore": vitals_before,
            "vitalsAfter": vitals_after,
            "escalationPhase": self._escalation_phase(),
            "procedurePhase": self._procedure_phase(),
            "activeComplication": self.active_complication,
            "pendingDecision": self.pending_decision,
            "pendingDecisionState": self.pending_decision_state,
            "decisionResult": decision_result,
            "events": list(self.events),
            "score": self.score,
        }

    def get_state(self) -> dict:
        return {
            "sessionId": "",
            "tick": self._tick,
            "totalTicks": self.procedure["totalTicks"],
            "vitals": self.vitals_engine.snapshot(),
            "procedureId": self.procedure["id"],
            "procedureName": self.procedure["name"],
            "patient": self.procedure["patient"],
            "escalationPhase": self._escalation_phase(),
            "procedurePhase": self._procedure_phase(),
            "activeComplication": self.active_complication,
            "pendingDecision": self.pending_decision,
            "pendingDecisionState": self.pending_decision_state,
            "score": self.score,
            "maxScore": self.max_score,
            "completed": self.completed,
            "decisionHistory": self.decision_history,
            "complicationsEncountered": sum(1 for d in self.decision_history if d["complicationTriggered"] is not None or not d["wasCorrect"]),
            "correctDecisions": sum(1 for d in self.decision_history if d["wasCorrect"]),
            "totalDecisions": len(self.decision_history),
        }

    def _escalation_phase(self) -> str:
        curve = self.procedure["escalationCurve"]
        t = self._tick or 1
        for phase_key in ("phase1", "phase2", "phase3", "phase4"):
            lo, hi = curve[phase_key]["tickRange"]
            if lo <= t <= hi:
                return {
                    "phase1": "stable_workup",
                    "phase2": "complication_risk",
                    "phase3": "active_complication",
                    "phase4": "crisis_management",
                }[phase_key]
        return "recovery_or_failure"

    def _procedure_phase(self) -> str:
        phases = self.procedure["phases"]
        if not phases:
            return "Unknown"
        progress = self._tick / self.procedure["totalTicks"]
        idx = min(math.floor(progress * len(phases)), len(phases) - 1)
        return phases[idx]["name"]

    def _complication_severity(self, phase: str) -> float:
        return {
            "stable_workup": 0.5,
            "complication_risk": 0.8,
            "active_complication": 1.0,
            "crisis_management": 1.3,
            "recovery_or_failure": 0.6,
        }.get(phase, 1.0)


# ─────────────────────────────────────────────────────────────────────────────
# Session + SessionManager (in‑memory, 30‑min TTL)
# ─────────────────────────────────────────────────────────────────────────────

class SimulationSession:
    def __init__(self, session_id: str, orchestrator: SimulationOrchestrator):
        self.id = session_id
        self.orchestrator = orchestrator
        self.created_at = time.time()
        self.last_access = time.time()

    def touch(self) -> None:
        self.last_access = time.time()

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.last_access) > (30 * 60)

    def next(self) -> dict:
        self.touch()
        return self.orchestrator.next()

    def submit_decision(self, decision_id: str, option_id: str) -> dict:
        self.touch()
        return self.orchestrator.submit_decision(decision_id, option_id)

    @property
    def state(self) -> dict:
        self.touch()
        s = self.orchestrator.get_state()
        s["sessionId"] = self.id
        return s


class SessionManager:
    def __init__(self):
        self.sessions: dict[str, SimulationSession] = {}
        self.lock = threading.RLock()

    def create(self, session_id: str, seed: int, procedure_id: str) -> SimulationSession:
        with self.lock:
            self._evict_expired()
            orch = SimulationOrchestrator(seed, procedure_id)
            session = SimulationSession(session_id, orch)
            self.sessions[session_id] = session
            return session

    def get(self, session_id: str) -> Optional[SimulationSession]:
        with self.lock:
            self._evict_expired()
            s = self.sessions.get(session_id)
            if s:
                s.touch()
            return s

    def delete(self, session_id: str) -> bool:
        with self.lock:
            return self.sessions.pop(session_id, None) is not None

    @property
    def size(self) -> int:
        with self.lock:
            return len(self.sessions)

    def _evict_expired(self) -> None:
        expired = [sid for sid, s in self.sessions.items() if s.is_expired]
        for sid in expired:
            self.sessions.pop(sid, None)
