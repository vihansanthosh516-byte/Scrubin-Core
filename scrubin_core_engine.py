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
    ARCHETYPE_PHASE_BUCKETS,
    ARCHETYPE_PROMPTS,
    ARCHETYPE_INTERVENTIONS,
    ESCALATION_LABELS,
    OPTION_PHASE_OVERRIDES,
    classify_phase,
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
        # Canonical Marsaglia xorshift32 (13, 17, 5) — the earlier port replaced
        # the state with each shifted value instead of XOR-ing it back, which
        # turned the generator into a doubling counter that dead-ends at 0 for
        # every seed. The middle shift MUST be SIGNED (`s >> 17`, JS `>>`), not
        # unsigned: JS right-shift sign-extends, and Python's `>>` on a signed
        # int is already arithmetic — so `_uint32(s) >> 17` here produced a
        # different stream from the JS engine (verified: draw 1 matched, draw 2
        # diverged). This is what keeps the two engines bit-exact.
        s = self.state
        s = _int32(s ^ _uint32(s << 13))
        s = _int32(s ^ (s >> 17))
        s = _int32(s ^ _uint32(s << 5))
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
    def __init__(self, initial_vitals: dict, rng: DeterministicRNG, risk_profile: dict, baseline_vitals: dict = None):
        self.vitals = dict(initial_vitals)
        self.rng = rng
        self.risk_profile = risk_profile
        self.baseline_vitals = dict(baseline_vitals) if baseline_vitals else dict(DEFAULT_VITALS)
        self.pending_effects: list[dict] = []  # [{ tick, effect: {key:val} }]
        self.deterioration = 0.0  # cumulative physiologic decline for telemetry
        # Post-resolution recovery window: while tick <= recovery_until, vitals
        # pull back toward baseline much faster and decline is suppressed, so a
        # correctly managed complication visibly normalizes the patient instead
        # of leaving them critical until the case ends.
        self.recovery_until = -1

    def begin_recovery_window(self, until_tick: int) -> None:
        """Open a post-resolution window where vitals recover toward baseline
        aggressively. Call once on a correct complication resolution."""
        self.recovery_until = max(self.recovery_until, until_tick)

    def in_recovery_window(self, tick: int) -> bool:
        return tick <= self.recovery_until

    def _deterioration_stress(self) -> float:
        """How physiologically compromised the patient currently is (>= 1.0).
        The deviation terms are superlinear (^1.35) so decline accelerates into
        a vicious cycle the sicker the patient gets — an untended patient
        spirals, a tended one declines slowly."""
        v = self.vitals
        extra = 0.0
        extra += max(0.0, (95.0 - v.get("bp_systolic", 120))) / 40.0
        extra += max(0.0, (95.0 - v.get("spo2", 98))) / 30.0
        extra += max(0.0, (v.get("heart_rate", 80) - 100.0)) / 80.0
        extra += max(0.0, (v.get("temperature", 37.0) - 37.8)) / 2.0
        extra += max(0.0, (v.get("respiratory_rate", 16) - 22.0)) / 20.0
        return 1.0 + extra ** 1.25

    def apply_deterioration(self, scale: float = 1.0) -> None:
        """Progressive physiologic failure: vitals trend downward over the case.
        Scaled by the procedure's risk profile and by current stress, so an
        untended patient spirals while a tended one declines slowly."""
        severity = self._deterioration_stress()
        rate = self.risk_profile.get("deterioration_rate", 1.0)
        d = rate * severity * scale
        v = self.vitals
        v["bp_systolic"] -= 0.19 * d
        v["bp_diastolic"] -= 0.12 * d
        v["spo2"] -= 0.11 * d
        v["heart_rate"] += 0.21 * d
        v["respiratory_rate"] += 0.07 * d
        v["temperature"] += 0.012 * d
        self.vitals = clamp_vitals(self.vitals)
        self.deterioration += d

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
        # During the post-resolution recovery window, pull back toward baseline
        # ~4x faster so a correct rescue is followed by visible normalization.
        pull = 0.08 if self.in_recovery_window(tick) else 0.02
        for key, target in self.baseline_vitals.items():
            current = self.vitals[key]
            # Physiologic noise is kept quiet so the deterioration trend (not
            # random walk) drives the clinical course — complications then
            # develop causally from the vitals, not from noise.
            drift = self.rng.next_float(-0.15, 0.15)
            self.vitals[key] += (target - current) * pull * recovery + drift
        due = [e for e in self.pending_effects if e["tick"] <= tick]
        for entry in due:
            for key, val in entry["effect"].items():
                if val is not None:
                    self.vitals[key] += val
        self.pending_effects = [e for e in self.pending_effects if e["tick"] > tick]
        self.vitals = clamp_vitals(self.vitals)
        self.cap_compensatory_bp()
        return self.snapshot()

    def cap_compensatory_bp(self, hard_cap: float = 160.0) -> None:
        """Fix: compensatory systolic spikes may never exceed 160 mmHg — or the
        patient's own baseline, whichever is higher. A patient in hypovolemic
        shock has no circulating volume left to generate 200+ mmHg, so the
        old refractory loop's +10/cycle climb is physiologically impossible."""
        ceiling = max(hard_cap, self.baseline_vitals.get("bp_systolic", 120.0))
        if self.vitals["bp_systolic"] > ceiling:
            self.vitals["bp_systolic"] = ceiling


class ComplicationEngine:
    def __init__(self, rng: DeterministicRNG, weights: dict, allowed: list, risk_profile: dict):
        self.rng = rng
        self.allowed = list(allowed)
        self.weights = self._normalize_weights(weights)
        self.risk_profile = risk_profile
        self.active: Optional[str] = None
        self.active_since_tick = -1
        # Consecutive ticks each complication's trigger condition has held.
        self.danger: dict[str, int] = {}
        # Fresh-episode semantics: complications correctly treated stay disqualified
        # from spontaneous re-triggering until their trigger vital clears the
        # threshold again. Without this, a patient whose BP is still < 88 after
        # bleeding control deterministically re-fires hemorrhage the moment the
        # post-resolution cooldown expires — recovery becomes futile.
        self.disqualified: set[str] = set()
        # Post-recovery stabilization: no spontaneous re-trigger of ANY complication
        # until the physiology clears every trigger threshold for one observation.
        # This stops the post-cooldown whack-a-mole where the same underlying
        # derangement (e.g. low BP after thrombosis) re-fires a different
        # complication 3 ticks after a correct recovery.
        self.awaiting_recovery: bool = False

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

    def resolve(self, comp: Optional[str] = None) -> None:
        self.active = None
        self.active_since_tick = -1
        self.danger = {}
        if comp:
            self.disqualified.add(comp)
        # Enter the stabilization window — cleared on the first observation where
        # no allowed complication's trigger criteria hold.
        self.awaiting_recovery = True

    def _condition_met(self, vitals: dict, vital: str, op: str, threshold: float) -> bool:
        val = vitals.get(vital)
        if val is None:
            return False
        return val < threshold if op == "<" else val > threshold

    def _margin(self, vitals: dict, vital: str, op: str, threshold: float) -> float:
        """How far past the threshold the vital is (0 when not met). Used to
        pick the dominant derangement deterministically when several are bad."""
        val = vitals.get(vital)
        if val is None:
            return 0.0
        if op == "<":
            return max(0.0, (threshold - val) / threshold)
        return max(0.0, (val - threshold) / threshold)

    def detect(self, tick: int, vitals: dict) -> Optional[tuple[str, str]]:
        """Causally detect a complication from sustained vital derangement.

        No dice rolls: a complication fires only when the physiology crosses a
        scientific threshold (e.g. SpO₂ < 92%) and stays there for consecutive
        observations. The most dominant derangement wins. Returns (complication,
        human-readable cause) or None."""
        if self.active:
            return None
        # Stabilization window: after a correct recovery, hold off all spontaneous
        # detection until the physiology clears every trigger threshold.
        if self.awaiting_recovery:
            still_deranged = any(
                all(self._condition_met(vitals, v, op, t) for v, op, t in COMPLICATION_TRIGGERS.get(comp, {}).get("criteria", []))
                for comp in self.allowed
                if comp in COMPLICATION_TRIGGERS
            )
            if still_deranged:
                return None
            self.awaiting_recovery = False
        # Re-arm resolved complications once their trigger derangement clears —
        # only a NEW episode (vital recovered, then crossed again) can re-fire.
        for comp in list(self.disqualified):
            trig = COMPLICATION_TRIGGERS.get(comp)
            if not trig:
                self.disqualified.discard(comp)
                continue
            if not all(self._condition_met(vitals, v, op, t) for v, op, t in trig["criteria"]):
                self.disqualified.discard(comp)
        candidates: list[tuple[int, float, str, str]] = []
        for comp in self.allowed:
            if comp in self.disqualified:
                continue
            trig = COMPLICATION_TRIGGERS.get(comp)
            if not trig:
                continue
            criteria = trig["criteria"]
            need = trig.get("persistence", 2)
            met = all(self._condition_met(vitals, v, op, t) for v, op, t in criteria)
            if met:
                self.danger[comp] = self.danger.get(comp, 0) + 1
            else:
                self.danger[comp] = 0
            if self.danger.get(comp, 0) >= need:
                margin = max(self._margin(vitals, v, op, t) for v, op, t in criteria)
                cause = _format_complication_cause(comp, vitals)
                candidates.append((self.danger[comp], margin, comp, cause))
        if not candidates:
            return None
        # Most sustained, then most severe derangement — deterministic.
        candidates.sort(key=lambda c: (-c[0], -c[1], c[2]))
        comp, cause = candidates[0][2], candidates[0][3]
        self.active = comp
        self.active_since_tick = tick
        self.danger = {}
        return comp, cause


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
        bucket = classify_phase(procedure_phase)
        if active_complication:
            archetype = self._pick_archetype_for_complication(archetypes, active_complication, bucket)
        else:
            archetype = self._pick_stock_archetype(archetypes, bucket)

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

        # Situation-aware option assembly: treating options are always offered
        # (recovery guarantee), then decoys are drawn in TWO TIERS — the chosen
        # archetype's own non-treating options first (thematically coherent, so
        # e.g. observe_hemostasis reliably accompanies BLEEDING_CONTROL), then a
        # random subset of phase-eligible options from other archetypes. This
        # keeps the offer clinically plausible for where the surgery is AND makes
        # consecutive decisions differ. With no active complication, the chosen
        # archetype's low-risk options are always offered and its high-risk
        # options are sampled.
        if active_complication:
            always = [o for o in options if active_complication in o["correctForComplications"]]
            exclude = {o["id"] for o in always}
            primary, secondary = self._decoy_pool(archetype, active_complication, bucket, exclude)
            chosen = self._sample_options(always, primary, secondary)
        else:
            always = [o for o in options if self._is_low_risk(o["riskIfWrong"])]
            decoys = [o for o in options if not self._is_low_risk(o["riskIfWrong"])]
            chosen = self._sample_options(always, decoys, [])

        if not (4 <= len(chosen) <= 8):
            raise RuntimeError(f"DecisionEngine: archetype {archetype} produced {len(chosen)} options, expected 4-8")

        self._shuffle(chosen)
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
            "options": chosen,
            "urgency": urgency,
        }

    @staticmethod
    def _is_low_risk(risk: dict) -> bool:
        return all((v is None or abs(v) < 8) for v in risk.values())

    def _decoy_pool(self, archetype: str, comp: str, bucket: str, exclude_ids: set) -> tuple:
        """Two-tier decoy pool: (primary) the chosen archetype's own non-treating
        options, (secondary) phase-eligible non-treating options from every other
        archetype. Primary options are clinically coherent with the treating
        options; secondary options add situation variety."""
        primary = []
        secondary = []
        seen = set(exclude_ids)

        def build(a: str, comp: str, bucket: str, seen: set) -> list:
            out = []
            archetype_buckets = ARCHETYPE_PHASE_BUCKETS[a]
            for iv in ARCHETYPE_INTERVENTIONS[a]:
                if comp in iv["treats"] or iv["id"] in seen:
                    continue
                # Option-level phase filter: an option is offerable when its own
                # bucket list (override ?? archetype) includes the current bucket.
                # Treating options are never filtered — only decoys.
                opt_buckets = OPTION_PHASE_OVERRIDES.get(iv["id"], archetype_buckets)
                if bucket not in opt_buckets:
                    continue
                seen.add(iv["id"])
                out.append({
                    "id": iv["id"],
                    "label": iv["label"],
                    "archetype": a,
                    "correctForComplications": list(iv["treats"]),
                    "effectOnVitals": dict(iv["vitalsEffect"]),
                    "riskIfWrong": dict(iv["riskIfWrong"]),
                    "feedback": {"correct": iv["correctFeedback"], "wrong": iv["wrongFeedback"]},
                })
            return out

        primary = build(archetype, comp, bucket, seen)
        for a in ARCHETYPE_PHASE_BUCKETS:
            if a != archetype:
                secondary += build(a, comp, bucket, seen)
        return primary, secondary

    def _sample_options(self, always: list, primary: list, secondary: list) -> list:
        """Always offer `always`; draw decoys from `primary` first (shuffled),
        then `secondary`, so the total lands in 4-8. Mirrored by the TS
        DecisionEngine. RNG-driven, so a fixed seed replays bit-identically."""
        total = len(always) + len(primary) + len(secondary)
        if total < 4:
            return list(always) + list(primary) + list(secondary)
        target = self.rng.next_int(4, min(8, total))
        need = min(max(target - len(always), 0), len(primary) + len(secondary))
        if len(always) + need < 4:
            need = min(4 - len(always), len(primary) + len(secondary))
        if need <= 0:
            return list(always)
        p = list(primary)
        self._shuffle(p)
        if need <= len(p):
            return list(always) + p[:need]
        s = list(secondary)
        self._shuffle(s)
        return list(always) + p + s[:need - len(p)]

    def _pick_stock_archetype(self, archetypes: list, bucket: str) -> str:
        eligible = [a for a in archetypes if bucket in ARCHETYPE_PHASE_BUCKETS.get(a, [])]
        if eligible:
            return self.rng.pick(eligible)
        return self.rng.pick(archetypes)

    def _pick_archetype_for_complication(self, archetypes, comp, bucket: str) -> str:
        matching = [a for a in archetypes if comp in ARCHETYPE_COMPLICATION_MAP.get(a, [])]
        eligible = [a for a in matching if bucket in ARCHETYPE_PHASE_BUCKETS.get(a, [])]
        if eligible:
            return self.rng.pick(eligible)
        if matching:
            return self.rng.pick(matching)
        global_matching = [a for a, comps in ARCHETYPE_COMPLICATION_MAP.items() if comp in comps]
        global_eligible = [a for a in global_matching if bucket in ARCHETYPE_PHASE_BUCKETS.get(a, [])]
        if global_eligible:
            return self.rng.pick(global_eligible)
        if global_matching:
            return self.rng.pick(global_matching)
        return self.rng.pick(archetypes)

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
# Physiology-driven complication science
# ─────────────────────────────────────────────────────────────────────────────
# Complications are NOT random: each one is caused by a sustained, measurable
# vital derangement. `criteria` are (vital, op, threshold) — ALL must hold.
# `persistence` is how many consecutive observations must stay past the
# threshold before the complication develops (2 = one observation in stock
# mode, since each /next advances one tick). Complications without criteria
# (anaphylaxis, nerve_injury) can only arise from surgical mistakes.
# After a complication resolves, hold ALL spontaneous detection for this many
# ticks so a correct recovery buys the trainee real clean play. The earlier
# 3-tick gate let a NEW complication (e.g. infection) re-fire as soon as 7 ticks
# after a correct hemorrhage recovery: the temp hovered just under its 38.3
# threshold, the stabilization window closed at the first clean observation,
# and two ticks later the fever crossed and re-entered branched mode — a ~5%
# flake that failed the live "no re-trigger" test in CI. With an 8-tick gate
# the soonest a spontaneous re-fire can occur is tick 10 (8 + persistence 2).
POST_RESOLUTION_STABILIZATION_TICKS = 8

COMPLICATION_TRIGGERS = {
    "hypoxia":            {"criteria": [("spo2", "<", 93.0)], "persistence": 2},
    "hemorrhage":         {"criteria": [("bp_systolic", "<", 88.0)], "persistence": 2},
    "infection":          {"criteria": [("temperature", ">", 38.3)], "persistence": 2},
    "cardiac_arrhythmia": {"criteria": [("heart_rate", ">", 135.0)], "persistence": 2},
    "thrombosis":         {"criteria": [("respiratory_rate", ">", 26.0)], "persistence": 2},
    "fluid_overload":     {"criteria": [("spo2", "<", 93.0), ("heart_rate", ">", 110.0)], "persistence": 3},
}


def _format_complication_cause(comp: str, vitals: dict) -> str:
    """Human-readable scientific explanation of why the complication developed.

    Threshold-honest: only claims a crossing the vitals actually show. Mistake-
    triggered complications can fire before vitals have fully deranged, so the
    cause then describes the oncoming physiologic failure instead of a false
    crossing.
    """
    v = vitals
    spo2 = v.get("spo2", 0)
    bp = v.get("bp_systolic", 0)
    hr = v.get("heart_rate", 0)
    temp = v.get("temperature", 0)
    rr = v.get("respiratory_rate", 0)

    def fmt_val(value, prec):
        return f"{value:.{prec}f}" if prec else f"{value:.0f}"

    def fell(value, thresh, unit, label, prec=0):
        if value < thresh:
            return f"{label} has fallen to {fmt_val(value, prec)}{unit} — below the {thresh:g}{unit} threshold"
        return f"{label} is {fmt_val(value, prec)}{unit} and dropping toward the {thresh:g}{unit} threshold"

    def rose(value, thresh, unit, label, prec=0):
        if value > thresh:
            return f"{label} has climbed to {fmt_val(value, prec)}{unit} — above the {thresh:g}{unit} threshold"
        return f"{label} is {fmt_val(value, prec)}{unit} and climbing toward the {thresh:g}{unit} threshold"

    causes = {
        "hypoxia":            f"Oxygen delivery is failing — {fell(spo2, 93.0, '%', 'SpO₂')}",
        "hemorrhage":         f"Hypovolemic shock is developing — {fell(bp, 88.0, ' mmHg', 'systolic BP')}",
        "infection":          f"Systemic inflammation is spreading — {rose(temp, 38.3, '°C', 'temperature', 1)}",
        "cardiac_arrhythmia": f"Unstable tachyarrhythmia — {rose(hr, 135.0, ' bpm', 'heart rate')}",
        "thrombosis":         f"Possible thromboembolism — {rose(rr, 26.0, '/min', 'respiratory rate')}",
        "fluid_overload":     f"Volume overload — {fell(spo2, 93.0, '%', 'SpO₂')} with tachycardia (HR {hr:.0f} bpm)",
        "anaphylaxis":        f"Anaphylactic reaction — airway and perfusion compromised (BP {bp:.0f} mmHg, SpO₂ {spo2:.0f}%)",
        "nerve_injury":       f"Peripheral nerve injury — motor and sensory function at risk",
    }
    return causes.get(comp, f"Physiologic derangement: {comp.replace('_', ' ')}")


DECAY_RATES = {
    "hypoxia":             {"spo2": -2.0, "heart_rate": +2.0, "respiratory_rate": +1.0, "bp_systolic": -1.0},
    "hemorrhage":          {"heart_rate": +4.0, "bp_systolic": -3.5, "bp_diastolic": -2.5, "spo2": -0.5, "respiratory_rate": +1.0},
    "infection":           {"temperature": +0.3, "heart_rate": +1.5, "bp_systolic": -1.0},
    "thrombosis":          {"heart_rate": +1.5, "bp_systolic": -2.0, "spo2": -1.0, "respiratory_rate": +0.8},
    "cardiac_arrhythmia":  {"heart_rate": +5.5, "bp_systolic": -3.0, "bp_diastolic": -2.0, "spo2": -0.8},
    "anaphylaxis":         {"heart_rate": +4.5, "bp_systolic": -4.5, "bp_diastolic": -3.0, "spo2": -1.5, "respiratory_rate": +1.5},
    "nerve_injury":        {"heart_rate": +1.5, "bp_systolic": +1.0, "respiratory_rate": +0.5},
    "fluid_overload":      {"spo2": -1.2, "heart_rate": +1.0, "bp_systolic": +1.5, "respiratory_rate": +0.8},
}


# ─────────────────────────────────────────────────────────────────────────────
# Dynamic patient physiology
# ─────────────────────────────────────────────────────────────────────────────
# Every session rolls a unique, medically plausible patient presentation from
# the session seed. Deltas adjust the procedure's own baseline (e.g. an already
# febrile appendicitis patient) by a moderate amount — the disease state stays,
# but no two patients are identical, and some present badly (septic/hypoxemic).

PATIENT_PRESENTATION_LABELS = {
    "compensated":  "Compensated / euvolaemic",
    "anxious":      "Anxious / mild sympathetic drive",
    "hypertensive": "Hypertensive",
    "dehydrated":   "Dehydrated / volume-contracted",
    "septic":       "Early sepsis / systemic inflammation",
    "hypoxemic":    "Mild hypoxemia / reduced pulmonary reserve",
    "fit":          "Physiologically fit / resting bradycardia",
}

PATIENT_PRESENTATION_DELTAS = {
    "compensated":  {},
    "anxious":      {"heart_rate": +8.0, "bp_systolic": +5.0, "bp_diastolic": +3.0, "respiratory_rate": +2.0},
    "hypertensive": {"heart_rate": -2.0, "bp_systolic": +16.0, "bp_diastolic": +9.0},
    "dehydrated":   {"heart_rate": +6.0, "bp_systolic": -6.0, "bp_diastolic": -4.0, "temperature": +0.2},
    "septic":       {"heart_rate": +12.0, "bp_systolic": -5.0, "bp_diastolic": -3.0, "spo2": -1.5, "respiratory_rate": +3.0, "temperature": +0.5},
    "hypoxemic":    {"heart_rate": +4.0, "spo2": -3.0, "respiratory_rate": +3.0},
    "fit":          {"heart_rate": -7.0, "bp_systolic": -4.0, "bp_diastolic": -2.0, "spo2": +1.0},
}

# Patients never START a case already inside an active complication trigger
# zone: the crisis has to DEVELOP during the operation (drift, step stress, or
# the moment you cut), not be pre-triggered at tick 1. These guardrails sit just
# outside the physiologic thresholds in COMPLICATION_TRIGGERS — a patient can
# begin visibly sick (borderline BP 90, febrile 38.2) and then cross the line
# mid-case, which reads as "the surgery is making them worse".
STARTING_VITAL_GUARDRAILS = {
    "bp_systolic":      (90.0, "max"),   # hemorrhage trigger < 88
    "bp_diastolic":     (55.0, "max"),
    "spo2":             (93.5, "max"),   # hypoxia trigger < 93
    "temperature":      (38.2, "min"),   # infection trigger > 38.3
    "heart_rate":       (133.0, "min"),  # arrhythmia trigger > 135
    "respiratory_rate": (25.5, "min"),   # thrombosis trigger > 26
}

ASA_MULTIPLIERS = {1: 0.8, 2: 1.0, 3: 1.3}          # presentation severity scaling
ASA_DETERIORATION = {1: 0.9, 2: 1.0, 3: 1.18}       # sicker patients decline faster
ASA_LABELS = {
    1: "ASA I (healthy)",
    2: "ASA II (mild systemic disease)",
    3: "ASA III (severe systemic disease)",
}

# Surgical-step physiologic responses (sympathetic surge on incision, vagal
# traction bradycardia, positional hypotension…). Applied transiently over a
# couple of ticks so the OR monitor visibly reacts to what the trainee does.
STEP_VITAL_EFFECTS = {
    "access":   {"heart_rate": +8.0, "bp_systolic": +10.0, "bp_diastolic": +5.0},  # painful stimulation / incision
    "exposure": {"heart_rate": -9.0, "bp_systolic": -5.0, "bp_diastolic": -3.0},   # visceral traction → vagal
    "dissect":  {"heart_rate": +5.0, "bp_systolic": +4.0, "bp_diastolic": +2.0},
    "core":     {"heart_rate": +4.0, "bp_systolic": +3.0, "bp_diastolic": +2.0},
    "position": {"heart_rate": -4.0, "bp_systolic": -6.0, "bp_diastolic": -4.0},   # positional hypotension
    "vessel":   {"heart_rate": +6.0, "bp_systolic": +5.0, "bp_diastolic": +3.0},
    "closure":  {"heart_rate": -3.0, "bp_systolic": -2.0},
}

# Step kinds where intraoperative bleeding can occur even with correct
# technique (friable tissue, anomalous vessels) — the "cut and it bleeds" cases.
STEP_BLEED_KINDS = ("vessel", "dissect", "access")


# ─────────────────────────────────────────────────────────────────────────────
# Orchestrator
# ─────────────────────────────────────────────────────────────────────────────

class SimulationOrchestrator:
    def __init__(self, seed: int, procedure_id: str):
        self.rng = DeterministicRNG(seed)
        # Warm up the main stream: this xorshift32's early outputs are tiny for
        # small seeds, which would skew the step-modifier rolls. The profile /
        # complication / decision engines all use clones taken BEFORE this.
        for _ in range(8):
            self.rng.next()
        self.procedure = get_procedure(procedure_id)
        if self.procedure is None:
            raise RuntimeError(f"Unknown procedure: {procedure_id}")

        vitals = dict(self.procedure["patient"]["baselineVitals"])
        vitals.update(self.procedure["initialState"]["vitals_override"])
        self.vitals_engine = VitalsEngine(
            vitals,
            self.rng.clone(),
            self.procedure["initialState"]["riskProfile"],
            baseline_vitals=self.procedure["patient"]["baselineVitals"]
        )
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
        self.mode = "stock"
        self.physiological_reserve = 100.0
        self.complication_count = 0
        # Wrong rescue attempts during the current complication crisis. Used by
        # the reserve-refund on resolution (Fix: renewable reserve — clean
        # management earns reserve back, fumbles reduce the refund).
        self._complication_wrong_attempts = 0
        # Where the active complication came from: "mistake" (surgical error via
        # /complicate) or "spontaneous" (physiologic deterioration). Used by the
        # UI to label the crisis and to avoid skipping a stock step the trainee
        # had not yet failed.
        self.complication_source: Optional[str] = None
        # Scientific, human-readable explanation of the active complication.
        self.complication_cause: Optional[str] = None
        # Tick on which the last complication resolved — no spontaneous detection
        # for POST_RESOLUTION_STABILIZATION_TICKS after it, so a correct recovery
        # buys the trainee real clean play before the physiology can re-trigger.
        self.last_resolved_tick = -10
        # ── Debrief evaluation data (persistent across tick resets) ──
        # Every stock step the client reports (via /next on correct, /complicate
        # on wrong). `self.events` is reset each tick, so this is the durable
        # record the post-case evaluation is built from.
        self.stock_history: list[dict] = []
        # Every complication that developed, with source/cause/tick/resolution.
        self.complication_history: list[dict] = []
        # Human-readable death cause, set by check_mortality().
        self.death_reason: Optional[str] = None

        # Unique per-session physiology (ASA class + presentation) rolled from
        # the seed, applied to starting AND homeostatic vitals.
        self.patient_profile = self._generate_patient_profile()
        # Intraoperative bleeding can occur at most once per run.
        self.step_bleed_fired = False
        self._bleed_step_rolled = False

    def _generate_patient_profile(self) -> dict:
        """Roll a unique ASA class + physiologic presentation from the session
        seed and adjust the patient's starting AND homeostatic vitals so every
        run feels different — and some patients present badly."""
        rng = self.rng.clone()
        # Warm up: this xorshift32's first output is proportional to the seed,
        # so rolls read straight off the top would all land in the first bucket.
        for _ in range(3):
            rng.next()
        roll = rng.next_float(0.0, 1.0)
        if roll < 0.30:
            presentation = "compensated"
        elif roll < 0.45:
            presentation = "anxious"
        elif roll < 0.58:
            presentation = "hypertensive"
        elif roll < 0.72:
            presentation = "dehydrated"
        elif roll < 0.86:
            presentation = "septic"
        elif roll < 0.93:
            presentation = "hypoxemic"
        else:
            presentation = "fit"

        asa_roll = rng.next_float(0.0, 1.0)
        asa = 1 if asa_roll < 0.30 else (2 if asa_roll < 0.70 else 3)

        deltas = PATIENT_PRESENTATION_DELTAS[presentation]
        mult = ASA_MULTIPLIERS[asa]
        profile = {
            "asaClass": asa,
            "asaLabel": ASA_LABELS[asa],
            "presentation": presentation,
            "presentationLabel": PATIENT_PRESENTATION_LABELS[presentation],
        }

        # Apply to the live vitals AND the homeostatic baseline so the drift
        # engine doesn't pull the patient back to the static registry values.
        for key, delta in deltas.items():
            applied = round(delta * mult, 1)
            if key in self.vitals_engine.vitals:
                self.vitals_engine.vitals[key] += applied
            if key in self.vitals_engine.baseline_vitals:
                self.vitals_engine.baseline_vitals[key] += applied
        # Starting guardrails: no patient begins inside a trigger zone. The
        # sickest presentations land ON the edge (BP 90, temp 38.2) so their
        # complication develops as the case proceeds.
        for vv in (self.vitals_engine.vitals, self.vitals_engine.baseline_vitals):
            for key, (limit, mode) in STARTING_VITAL_GUARDRAILS.items():
                if key not in vv:
                    continue
                if mode == "max":
                    vv[key] = max(limit, vv[key])
                else:
                    vv[key] = min(limit, vv[key])
        self.vitals_engine.vitals = clamp_vitals(self.vitals_engine.vitals)
        self.vitals_engine.baseline_vitals = clamp_vitals(self.vitals_engine.baseline_vitals)

        # Sicker patients: faster deterioration.
        risk = self.procedure["initialState"]["riskProfile"]
        risk["deterioration_rate"] = round(risk.get("deterioration_rate", 1.0) * ASA_DETERIORATION[asa], 3)
        return profile

    def _apply_step_modifier(self, step_kind: Optional[str], step_label: Optional[str]) -> Optional[dict]:
        """Real-time physiologic response to the surgical step just performed:
        transient vital shifts (incision → sympathetic surge, traction → vagal
        bradycardia) and, on vessel/dissection steps, a chance of intraoperative
        bleeding even with correct technique."""
        if not step_kind:
            return None
        kind = step_kind.lower()

        effect = STEP_VITAL_EFFECTS.get(kind)
        if effect:
            scaled = {k: round(v * self.rng.next_float(0.7, 1.3), 2) for k, v in effect.items()}
            # Apply the shift IMMEDIATELY so the OR monitor reacts the moment the
            # step lands, then schedule the reversal over the next two ticks.
            for key, val in scaled.items():
                if key in self.vitals_engine.vitals:
                    self.vitals_engine.vitals[key] += val
            self.vitals_engine.vitals = clamp_vitals(self.vitals_engine.vitals)
            reversal = {k: -v for k, v in scaled.items()}
            self.vitals_engine.apply_intervention(reversal, spread_over_ticks=2, current_tick=self._tick)
            self.events.append(f"Physiologic response to step: {kind}")

        # Intraoperative bleeding — rare ("sometimes bad"), at most once per run.
        # The FIRST surgical step gets a higher "signature moment" chance (the
        # incision can always bleed) — later steps roll lower odds.
        if (
            kind in STEP_BLEED_KINDS
            and self.active_complication is None
            and not self.completed
            and not self.step_bleed_fired
        ):
            # The FIRST surgical step is the signature "moment you cut" — it
            # carries the highest surprise-bleed odds. Later steps roll lower
            # so the case stays mostly clean with the occasional crisis.
            if self._bleed_step_rolled:
                base = 0.07 if kind == "vessel" else 0.04
            else:
                base = 0.16 if kind == "vessel" else 0.11
            self._bleed_step_rolled = True
            asa_mult = ASA_MULTIPLIERS.get(self.patient_profile["asaClass"], 1.0)
            risk = self.procedure["initialState"]["riskProfile"].get("base_complication_chance", 0.2)
            chance = base * asa_mult * (0.7 + 0.6 * risk)
            if self.rng.next_float(0.0, 1.0) < chance:
                self.step_bleed_fired = True
                return self._enter_step_bleed(kind, step_label)
        return None

    def _enter_step_bleed(self, kind: str, step_label: Optional[str]) -> Optional[dict]:
        """Intraoperative bleeding that surprises the surgeon: correct technique,
        friable tissue / anomalous vessel. No reserve penalty (it is not a
        mistake) — the patient is just in crisis and must be tended to."""
        allowed = self.procedure.get("allowedComplications") or list(self.comp_engine.allowed)
        if "hemorrhage" in allowed:
            comp = "hemorrhage"
        else:
            candidates = [c for c in ("hemorrhage", "infection", "hypoxia", "cardiac_arrhythmia") if c in allowed]
            if not candidates:
                return None
            comp = candidates[0]
        step = step_label or f"the {kind} step"
        cause = f"Intraoperative bleeding during '{step}' — friable tissue despite correct technique."
        self.mode = "branched"
        self.complication_count += 1
        self.active_complication = comp
        self.complication_source = "spontaneous"
        self.complication_cause = cause
        self.complication_history.append({
            "complication": comp,
            "source": "spontaneous",
            "cause": cause,
            "tick": self._tick,
            "reserve": self.physiological_reserve,
            "resolved": False,
            "resolvedTick": None,
        })
        effects = COMPLICATION_VITAL_EFFECTS.get(comp)
        if effects:
            for key, val in effects.items():
                if val is not None and key in self.vitals_engine.vitals:
                    self.vitals_engine.vitals[key] += val * 0.25
            self.vitals_engine.vitals = clamp_vitals(self.vitals_engine.vitals)
        self.events.append(
            f"⚠️ INTRAOPERATIVE BLEEDING: {comp.replace('_', ' ').upper()} during '{step}' (Reserve: {self.physiological_reserve}%)"
        )
        procedure_phase = self._procedure_phase()
        self.pending_decision = self.decision_engine.generate_decision(
            self._tick, self.vitals_engine.snapshot(), "active_complication", comp, procedure_phase
        )
        self.pending_decision_state = {"tick": self._tick, "decisionId": self.pending_decision["id"], "resolved": False}
        return self._build_result(None)

    def next(self, step_label: Optional[str] = None, step_kind: Optional[str] = None) -> dict:
        if self.completed:
            return self._build_result(None)

        if self.mode == "stock":
            self._tick += 1
            self.events = []
            if self._tick == 1:
                self.events.append(
                    f"Patient profile: {self.patient_profile['asaLabel']} — {self.patient_profile['presentationLabel']}."
                )
            # The step just completed can move the physiology (incision surge,
            # traction bradycardia) — or, on vessel steps, bleed.
            bleed = self._apply_step_modifier(step_kind, step_label)
            if bleed:
                return bleed
            vitals_before = self.vitals_engine.snapshot()
            # Progressive deterioration: the patient's physiology declines as the
            # case advances. Complications are CAUSAL — they develop when a
            # vital crosses its scientific threshold and stays there. After a
            # correct resolution the recovery window is open, so decline is
            # paused while the patient visibly stabilizes.
            if not self.vitals_engine.in_recovery_window(self._tick):
                self.vitals_engine.apply_deterioration()
            vitals_after = self.vitals_engine.tick(self._tick)
            cooldown_ok = self._tick - self.last_resolved_tick >= POST_RESOLUTION_STABILIZATION_TICKS
            trigger = self.comp_engine.detect(self._tick, vitals_after) if cooldown_ok else None
            if trigger:
                comp, cause = trigger
                return self._enter_spontaneous_complication(comp, cause)
            return self._build_result(None, vitals_before, vitals_after)

        if self.pending_decision_state and not self.pending_decision_state["resolved"]:
            raise RuntimeError("Cannot advance tick without decision")

        self._tick += 1
        self.events = []

        vitals_before = self.vitals_engine.snapshot()

        if self.mode == "branched":
            self.decay_vitals()
            # An untended patient keeps declining even while a complication is active.
            self.vitals_engine.apply_deterioration(0.15)
            if self.check_mortality():
                return self._build_result(None, vitals_before, self.vitals_engine.snapshot())

        escalation = self._escalation_phase()
        procedure_phase = self._procedure_phase()
        self.pending_decision = self.decision_engine.generate_decision(
            self._tick, self.vitals_engine.snapshot(), escalation, self.active_complication, procedure_phase
        )
        self.pending_decision_state = {"tick": self._tick, "decisionId": self.pending_decision["id"], "resolved": False}

        vitals_after = self.vitals_engine.tick(self._tick)
        self.max_score += 10
        return self._build_result(None, vitals_before, vitals_after)

    def record_stock_step(self, index: int, correct: bool, label: Optional[str] = None, kind: Optional[str] = None) -> None:
        """Record a reported stock-step outcome so the debrief evaluation can
        see the whole case (the engine never observes stock steps otherwise —
        the client owns them and only reports correct steps via /next and wrong
        steps via /complicate)."""
        self.stock_history.append({
            "index": int(index),
            "label": label or f"Step {int(index) + 1}",
            "kind": kind,
            "correct": bool(correct),
            "tick": self._tick,
        })

    def trigger_complication(self, complication_id: str, step_index: Optional[int] = None, step_label: Optional[str] = None, step_kind: Optional[str] = None) -> dict:
        if step_index is not None:
            self.record_stock_step(step_index, False, step_label, step_kind)
        self.mode = "branched"
        self.complication_count += 1
        self.physiological_reserve -= 25.0
        self._complication_wrong_attempts = 0

        if self.physiological_reserve <= 0:
            self.mode = "deceased"
            self.completed = True
            self.death_reason = "Irreversible Decompensatory Shock (Physiological reserve exhausted)"
            self.events.append("🔴 CRITICAL FAILURE: Irreversible Decompensatory Shock (Physiological reserve exhausted).")
            self.complication_history.append({
                "complication": complication_id,
                "source": "mistake",
                "cause": self.death_reason,
                "tick": self._tick,
                "reserve": self.physiological_reserve,
                "resolved": False,
                "resolvedTick": None,
            })
            return self._build_result(None)

        self.active_complication = complication_id
        self.complication_source = "mistake"
        self.complication_cause = _format_complication_cause(complication_id, self.vitals_engine.snapshot())
        self.complication_history.append({
            "complication": complication_id,
            "source": "mistake",
            "cause": self.complication_cause,
            "tick": self._tick,
            "reserve": self.physiological_reserve,
            "resolved": False,
            "resolvedTick": None,
        })
        
        # Apply initial complication vital hit immediately (50% of the total effect)
        effects = COMPLICATION_VITAL_EFFECTS.get(complication_id)
        if effects:
            for key, val in effects.items():
                if val is not None:
                    self.vitals_engine.vitals[key] += val * 0.5
            self.vitals_engine.vitals = clamp_vitals(self.vitals_engine.vitals)
            
        self.events.append(f"⚠️ COMPLICATION TRIGGERED: {complication_id.replace('_', ' ').upper()} (Reserve: {self.physiological_reserve}%)")
        
        # Generate recovery decision
        procedure_phase = self._procedure_phase()
        escalation = "active_complication"
        self.pending_decision = self.decision_engine.generate_decision(
            self._tick, self.vitals_engine.snapshot(), escalation, complication_id, procedure_phase
        )
        self.pending_decision_state = {"tick": self._tick, "decisionId": self.pending_decision["id"], "resolved": False}
        
        return self._build_result(None)

    def _enter_spontaneous_complication(self, complication_id: str, cause: str) -> dict:
        """The patient's own physiology fails: sustained vital derangement caused
        this complication. It does not cost physiological reserve (reserve is the
        penalty meter for surgical mistakes) but the patient is now in crisis
        and must be tended to."""
        self.mode = "branched"
        self.complication_count += 1
        self._complication_wrong_attempts = 0
        self.active_complication = complication_id
        self.complication_source = "spontaneous"
        self.complication_cause = cause
        self.complication_history.append({
            "complication": complication_id,
            "source": "spontaneous",
            "cause": cause,
            "tick": self._tick,
            "reserve": self.physiological_reserve,
            "resolved": False,
            "resolvedTick": None,
        })

        # Apply the complication's initial vital hit gently (25% of total
        # effect): spontaneous crises come from slow deterioration, not a
        # surgical misstep, so the instant damage is much softer than the
        # mistake-triggered path (which uses 50%).
        effects = COMPLICATION_VITAL_EFFECTS.get(complication_id)
        if effects:
            for key, val in effects.items():
                if val is not None:
                    self.vitals_engine.vitals[key] += val * 0.25
            self.vitals_engine.vitals = clamp_vitals(self.vitals_engine.vitals)

        self.events.append(
            f"⚠️ PATIENT DETERIORATING: {complication_id.replace('_', ' ').upper()} developed spontaneously (Reserve: {self.physiological_reserve}%)"
        )

        # Generate the recovery decision the trainee must tend to
        procedure_phase = self._procedure_phase()
        escalation = "active_complication"
        self.pending_decision = self.decision_engine.generate_decision(
            self._tick, self.vitals_engine.snapshot(), escalation, complication_id, procedure_phase
        )
        self.pending_decision_state = {"tick": self._tick, "decisionId": self.pending_decision["id"], "resolved": False}

        return self._build_result(None)

    def decay_vitals(self):
        if self.mode != "branched":
            return

        # Science-based reserve drain based on critical vitals
        v = self.vitals_engine.snapshot()
        bp = v.get("bp_systolic", 120)
        spo2 = v.get("spo2", 98)

        if bp < 70 or spo2 < 85:
            self.physiological_reserve -= 2.5
            self.events.append(f"⚠️ Physiological reserve draining due to ischemia/hypoxia: {self.physiological_reserve}%")

        comp = self.active_complication
        if not comp or comp not in DECAY_RATES:
            return
        rates = DECAY_RATES[comp]
        for key, val in rates.items():
            self.vitals_engine.vitals[key] += val
        self.vitals_engine.vitals = clamp_vitals(self.vitals_engine.vitals)

    def check_mortality(self) -> bool:
        v = self.vitals_engine.snapshot()
        reasons = []
        if self.physiological_reserve <= 0:
            reasons.append("Irreversible Multi-Organ Failure (Physiological reserve depleted)")
        if v["bp_systolic"] < 40:
            reasons.append("Severe Hypotension (BP < 40)")
        if v["spo2"] < 65:
            reasons.append("Severe Hypoxia (SpO2 < 65%)")
        if v["heart_rate"] > 180:
            reasons.append("Uncontrolled tachyarrhythmia (HR > 180)")
        if v["heart_rate"] < 30:
            reasons.append("Severe bradycardia (HR < 30)")

        if reasons:
            self.mode = "deceased"
            self.completed = True
            self.death_reason = ", ".join(reasons)
            self.events.append(f"🔴 CRITICAL FAILURE: Patient died of {self.death_reason}.")
            return True
        return False

    def tick_vitals_only(self) -> dict:
        if self.completed:
            return self.get_state()
            
        vitals_before = self.vitals_engine.snapshot()
        
        if self.mode == "stock":
            # Gentle real-time decline so the deteriorating patient is visible
            # between steps, plus normal drift/recovery around baseline.
            self.vitals_engine.apply_deterioration(0.05)
            self.vitals_engine.tick(self._tick)
        elif self.mode == "branched":
            # Decay vitals based on active complication
            self.decay_vitals()
            # Check mortality
            if self.check_mortality():
                return self.get_state()
            # Also run normal vitals engine tick for normal drift/recovery
            self.vitals_engine.tick(self._tick)
            
        return self.get_state()

    def submit_decision(self, decision_id: str, option_id: str) -> dict:
        if not self.pending_decision or self.pending_decision["id"] != decision_id:
            raise RuntimeError("Invalid decision ID or no pending decision")
        if not self.pending_decision_state or self.pending_decision_state["resolved"]:
            raise RuntimeError("No pending decision to resolve")

        vitals_before = self.vitals_engine.snapshot()
        # Capture the complication source before resolution clears it, so the
        # client can tell a spontaneous crisis (no step skipped) from a mistake.
        source_before = self.complication_source
        eval_ = self.decision_engine.evaluate_decision(self.pending_decision, option_id, vitals_before, self.active_complication)
        self.score += eval_["scoreDelta"]

        if eval_["wasCorrect"]:
            self.vitals_engine.apply_intervention(eval_["vitalsEffect"], 3, self._tick)
            self.events.append(eval_["feedback"])
            if self.active_complication:
                if self.physiological_reserve < 30.0:
                    # Fix 2: no infinite phantom loop. Reserve below 30% with an
                    # active complication is the point of no return — the engine
                    # hard-transitions to terminal failure instead of rewarding
                    # every correct pick with a +10 mmHg spike that never clears.
                    self.mode = "deceased"
                    self.completed = True
                    self.death_reason = "Irreversible Refractory Shock / DIC (physiologic reserve critically depleted)"
                    self.events.append("🔴 CRITICAL FAILURE: Patient has entered irreversible Refractory Shock / DIC. Standard protocols are failing.")
                else:
                    resolved_comp = self.active_complication
                    self.comp_engine.resolve(resolved_comp)
                    self.active_complication = None
                    self.complication_source = None
                    self.complication_cause = None
                    self.last_resolved_tick = self._tick
                    # Post-resolution recovery window: pull the deranged vitals
                    # back toward baseline over the next few ticks so a correct
                    # rescue is followed by visible normalization rather than a
                    # patient who stays critical to the end of the case.
                    self.vitals_engine.begin_recovery_window(self._tick + POST_RESOLUTION_STABILIZATION_TICKS)
                    # Mark the currently-active complication as resolved in the
                    # durable history the debrief evaluation reads.
                    for entry in reversed(self.complication_history):
                        if not entry.get("resolved"):
                            entry["resolved"] = True
                            entry["resolvedTick"] = self._tick
                            break
                    self.events.append("Complication resolved")
                    # Fix 1: renewable reserve — reward clean management. Refund
                    # up to 15% reserve for a first-try rescue, minus 5% per
                    # wrong attempt (floor 0), so a skilled surgeon can absorb
                    # 3-4 mistakes across a long case instead of being doomed
                    # the moment the 3rd complication fires.
                    refund = max(0.0, 15.0 - 5.0 * self._complication_wrong_attempts)
                    self._complication_wrong_attempts = 0
                    if refund > 0:
                        self.physiological_reserve = min(100.0, self.physiological_reserve + refund)
                        self.events.append(f"✅ {refund:.0f}% physiological reserve restored for clean management")
                    # Transition back to stock
                    self.mode = "stock"
        else:
            self._complication_wrong_attempts += 1
            self.vitals_engine.apply_intervention(eval_["vitalsEffect"], 1, self._tick)
            if eval_["complicationTriggered"] and not self.active_complication:
                self.active_complication = eval_["complicationTriggered"]
                self._complication_wrong_attempts = 0
                self.vitals_engine.apply_complication(eval_["complicationTriggered"], 0.7)
                self.events.append(f"Wrong decision triggered: {eval_['complicationTriggered'].replace('_', ' ')}")
                self.complication_history.append({
                    "complication": eval_["complicationTriggered"],
                    "source": "mistake",
                    "cause": _format_complication_cause(eval_["complicationTriggered"], self.vitals_engine.snapshot()),
                    "tick": self._tick,
                    "reserve": self.physiological_reserve,
                    "resolved": False,
                    "resolvedTick": None,
                })
            self.events.append(eval_["feedback"])

        # Fix 3: cap any compensatory systolic spike before it reaches the client.
        self.vitals_engine.cap_compensatory_bp()

        result = {
            "decisionId": decision_id,
            "optionId": option_id,
            "tick": self._tick,
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

        res = self._build_result(result, result["vitalsBefore"], result["vitalsAfter"])
        res["complicationSource"] = source_before
        return res

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
            "mode": self.mode,
            "physiologicalReserve": self.physiological_reserve,
            "complicationCount": self.complication_count,
            "complicationSource": self.complication_source,
            "complicationCause": self.complication_cause,
            "deterioration": self.vitals_engine.deterioration,
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
            "patientProfile": self.patient_profile,
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
            "mode": self.mode,
            "physiologicalReserve": self.physiological_reserve,
            "complicationCount": self.complication_count,
            "complicationSource": self.complication_source,
            "complicationCause": self.complication_cause,
            "deterioration": self.vitals_engine.deterioration,
            "correctSteps": sum(1 for s in self.stock_history if s["correct"]),
            "totalSteps": len(self.stock_history),
            "stockHistory": list(self.stock_history),
            "complicationHistory": list(self.complication_history),
            "deathReason": self.death_reason,
            # The debrief payload — present only once the case is over, which is
            # exactly when the UI renders the Debrief tab.
            "evaluation": self.build_evaluation() if self.completed else None,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Post-case debrief evaluation (deterministic, built from the session's
    # durable records: stock history, decision history, complication history)
    # ─────────────────────────────────────────────────────────────────────────

    def build_evaluation(self) -> dict:
        """Deterministic post-case debrief payload, generated on completion or
        death. Replaces the client-side fallback: every number is derived from
        what actually happened in this session, so identical play yields an
        identical report.

        Contract (consumed by client/src/components/DebriefReport.tsx):
          final_score, competency_score, safety_score, efficiency_score (0-100)
          patient_outcome (str)
          timeline_summary: [{tick, description}]
          critical_events:  [{severity, tick, description}]
          mistakes:         [{tick, description}]
          strengths:        [{description}]
          recommendations:  [{description}]
        """
        stock = list(self.stock_history)
        decisions = list(self.decision_history)
        comps = list(self.complication_history)

        stock_correct = sum(1 for s in stock if s["correct"])
        stock_total = len(stock)
        dec_correct = sum(1 for d in decisions if d["wasCorrect"])
        dec_total = len(decisions)
        mistake_comps = sum(1 for c in comps if c["source"] == "mistake")
        spontaneous_comps = sum(1 for c in comps if c["source"] == "spontaneous")
        total_comps = len(comps)

        is_deceased = self.mode == "deceased"

        def clamp(n: float, lo: float = 0.0, hi: float = 100.0) -> int:
            return max(int(lo), min(int(hi), round(n)))

        # ── Competency: accuracy on the surgical steps + crisis decisions ──
        stock_acc = (stock_correct / stock_total) if stock_total else 1.0
        dec_acc = (dec_correct / dec_total) if dec_total else 1.0
        competency = clamp(100.0 * (0.45 * stock_acc + 0.55 * dec_acc))
        # Each complication that had to be managed cost focus and time.
        competency = clamp(competency - 2.0 * min(total_comps, 10))
        # An UNRESOLVED complication is the trainee's failure to tend the
        # patient — a big competency hit (pure neglect must never score high).
        unresolved = sum(1 for c in comps if not c.get("resolved"))
        competency = clamp(competency - 15.0 * unresolved)

        # ── Safety: patient-centered physiology ──
        safety = 100.0
        for c in comps:
            resolved = c.get("resolved", False)
            if c["source"] == "mistake":
                safety -= 5.0 if resolved else 12.0   # preventable surgical error
            else:
                safety -= 2.0 if resolved else 8.0    # physiology under care
        safety -= 7.0 * (dec_total - dec_correct)  # wrong rescue decisions
        base = self.procedure["patient"]["baselineVitals"]
        v = self.vitals_engine.snapshot()
        deviation = min(
            20.0,
            abs(v.get("spo2", 98) - base.get("spo2", 98)) * 3.0
            + abs(v.get("bp_systolic", 120) - base.get("bp_systolic", 120)) * 0.6
            + abs(v.get("heart_rate", 80) - base.get("heart_rate", 80)) * 0.8
            + abs(v.get("temperature", 37.0) - base.get("temperature", 37.0)) * 6.0
            + abs(v.get("respiratory_rate", 16) - base.get("respiratory_rate", 16)) * 0.4,
        )
        safety -= deviation * 0.5
        safety -= max(0.0, 50.0 - self.physiological_reserve) * 0.3  # reserve lost
        if is_deceased:
            safety = 12
        safety = clamp(safety)

        # ── Efficiency: case length vs the authored plan ──
        authored = max(1, int(self.procedure["totalTicks"]))
        efficiency = clamp(100.0 * authored / max(1.0, float(self._tick)))
        # A death is never efficient — the case ended in failure, not on time.
        if is_deceased:
            efficiency = min(efficiency, 40)
            competency = min(competency, 45)

        final_score = clamp(0.4 * safety + 0.4 * competency + 0.2 * efficiency)

        # ── Patient outcome ──
        if is_deceased:
            outcome = "Deceased"
        else:
            tol = {
                "spo2": 4.0,
                "bp_systolic": 18.0,
                "bp_diastolic": 12.0,
                "heart_rate": 22.0,
                "temperature": 0.8,
                "respiratory_rate": 5.0,
            }
            deranged = any(
                abs(v.get(k, base.get(k, 0)) - base.get(k, 0)) > t
                for k, t in tol.items()
            )
            outcome = "Stabilized / Transferred" if deranged else "Stable / Discharged"

        def _step_label(s: dict) -> str:
            return s.get("label") or f"Step {int(s.get('index', 0)) + 1}"

        # ── Timeline (merged, sorted by tick, capped) ──
        timeline: list[dict] = []
        for s in stock:
            timeline.append({
                "tick": s.get("tick"),
                "description": f"{'✅ Completed' if s['correct'] else '❌ Missed'} surgical step — {_step_label(s)}",
            })
        for c in comps:
            timeline.append({
                "tick": c.get("tick"),
                "description": f"⚠️ {c['complication'].replace('_', ' ').upper()} developed ({c['source']})",
            })
            if c.get("resolved"):
                timeline.append({
                    "tick": c.get("resolvedTick"),
                    "description": "✅ Complication resolved",
                })
        for d in decisions:
            verdict = "✅ Correctly managed" if d["wasCorrect"] else "❌ Wrong decision"
            timeline.append({
                "tick": d.get("tick"),
                "description": f"{verdict}: {d['feedback']}",
            })
        if is_deceased:
            timeline.append({
                "tick": self._tick,
                "description": f"🔴 Patient died — {self.death_reason or 'physiologic collapse'}",
            })
        timeline.sort(key=lambda e: (e["tick"] if e["tick"] is not None else -1))
        timeline = timeline[-60:]

        # ── Critical events ──
        critical: list[dict] = []
        for c in comps:
            critical.append({
                "severity": "SURGICAL ERROR" if c["source"] == "mistake" else "DETERIORATION",
                "tick": c.get("tick"),
                "description": f"{c['complication'].replace('_', ' ').upper()} — {c.get('cause') or 'Physiologic derangement'}",
            })
        if is_deceased:
            critical.append({
                "severity": "FATAL",
                "tick": self._tick,
                "description": f"Patient died — {self.death_reason or 'physiologic collapse'}",
            })

        # ── Mistakes ──
        mistakes: list[dict] = []
        for s in stock:
            if not s["correct"]:
                mistakes.append({
                    "tick": s.get("tick"),
                    "description": f"Missed surgical step: {_step_label(s)}",
                })
        for d in decisions:
            if not d["wasCorrect"]:
                mistakes.append({"tick": d.get("tick"), "description": d["feedback"]})
        mistakes = mistakes[-15:]

        # ── Strengths ──
        strengths: list[dict] = []
        if stock_total:
            strengths.append({
                "description": f"Completed {stock_correct} of {stock_total} surgical steps correctly on first attempt",
            })
        if dec_total:
            strengths.append({
                "description": f"Correctly managed {dec_correct} of {dec_total} crisis decisions",
            })
        for d in decisions:
            if d["wasCorrect"]:
                strengths.append({"description": d["feedback"]})
                if len(strengths) >= 7:
                    break

        # ── Recommendations (deterministic rule set) ──
        recommendations: list[dict] = []
        if is_deceased:
            recommendations.append({
                "description": "Perform a structured post-mortem debrief: reconstruct the sequence of physiologic deterioration and re-examine every decision in the final crisis phase.",
            })
        if total_comps:
            last_comp = comps[-1]["complication"]
            recommendations.append({
                "description": f"Rehearse the rescue algorithm for {last_comp.replace('_', ' ')} — early recognition is the highest-yield skill in this procedure.",
            })
        if mistake_comps:
            recommendations.append({
                "description": "Review instrument handling and tissue planes: each missed step was a preventable surgical error that cost the patient time and physiologic reserve.",
            })
        if dec_total and dec_acc < 0.8:
            recommendations.append({
                "description": "Drill crisis decision-making: wrong rescue choices prolong the emergency and consume the patient's reserve.",
            })
        if efficiency < 85:
            recommendations.append({
                "description": "Focus on operative efficiency — every complication cycle lengthens anesthetic time and blood loss.",
            })
        if safety < 80:
            recommendations.append({
                "description": "Rehearse hemodynamic management and blood-loss thresholds before closure.",
            })
        if stock_total and stock_acc < 1.0:
            recommendations.append({
                "description": "Rehearse the step sequence end-to-end before the next case — missed steps break the sterile plan.",
            })
        recommendations.append({
            "description": "Perform a formal surgical time-out at every critical phase transition — identity, site, consent, and counts.",
        })
        recommendations.append({
            "description": "Debrief the team on postoperative monitoring — anticipate deterioration rather than reacting to it.",
        })
        recommendations = recommendations[:6]

        return {
            "final_score": final_score,
            "competency_score": competency,
            "safety_score": safety,
            "efficiency_score": efficiency,
            "patient_outcome": outcome,
            "timeline_summary": timeline,
            "critical_events": critical,
            "mistakes": mistakes,
            "strengths": strengths,
            "recommendations": recommendations,
            "generated_by": "scrubin-core",
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

    def next(self, step_label: Optional[str] = None, step_kind: Optional[str] = None) -> dict:
        self.touch()
        return self.orchestrator.next(step_label=step_label, step_kind=step_kind)

    def trigger_complication(self, complication_id: str, step_index: Optional[int] = None, step_label: Optional[str] = None, step_kind: Optional[str] = None) -> dict:
        self.touch()
        return self.orchestrator.trigger_complication(complication_id, step_index, step_label, step_kind)

    def tick_vitals_only(self) -> dict:
        self.touch()
        return self.orchestrator.tick_vitals_only()

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
