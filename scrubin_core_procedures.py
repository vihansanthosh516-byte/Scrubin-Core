"""Scrubin-Core procedure registry & clinical data definitions.

Matches the TypeScript originals in ``server/engine`` exactly:
  - DEFAULT_VITALS, VITAL_RANGES, clamp_vitals
  - COMPLICATION_VITAL_EFFECTS, ARCHETYPE_COMPLICATION_MAP
  - ESCALATION_LABELS, ARCHETYPE_PROMPTS, ARCHETYPE_INTERVENTIONS
  - Risk profiles & build_escalation
  - All 31 surgical procedure definitions
"""

from __future__ import annotations
import copy
import math
from typing import Any, Dict, List, Optional

# ── Core Vitals ──
DEFAULT_VITALS: Dict[str, float] = {
    "spo2": 98.0,
    "heart_rate": 72.0,
    "bp_systolic": 120.0,
    "bp_diastolic": 80.0,
    "temperature": 37.0,
    "respiratory_rate": 16.0,
}

VITAL_RANGES: Dict[str, tuple[float, float]] = {
    "spo2": (40.0, 100.0),
    "heart_rate": (20.0, 220.0),
    "bp_systolic": (30.0, 250.0),
    "bp_diastolic": (20.0, 150.0),
    "temperature": (30.0, 44.0),
    "respiratory_rate": (4.0, 60.0),
}


def clamp_vitals(v: Dict[str, float]) -> Dict[str, float]:
    result = {
        "spo2": max(VITAL_RANGES["spo2"][0], min(VITAL_RANGES["spo2"][1], v["spo2"])),
        "heart_rate": max(VITAL_RANGES["heart_rate"][0], min(VITAL_RANGES["heart_rate"][1], v["heart_rate"])),
        "bp_systolic": max(VITAL_RANGES["bp_systolic"][0], min(VITAL_RANGES["bp_systolic"][1], v["bp_systolic"])),
        "bp_diastolic": max(VITAL_RANGES["bp_diastolic"][0], min(VITAL_RANGES["bp_diastolic"][1], v["bp_diastolic"])),
        "temperature": max(VITAL_RANGES["temperature"][0], min(VITAL_RANGES["temperature"][1], v["temperature"])),
        "respiratory_rate": max(VITAL_RANGES["respiratory_rate"][0], min(VITAL_RANGES["respiratory_rate"][1], v["respiratory_rate"])),
    }
    # Physiologic invariant: diastolic pressure can never reach or exceed systolic.
    # Clamp it below systolic (keeping the systolic reading — and therefore the
    # BP < 40 mortality check — as the anchor) so inverted readings like 39.6/61.9
    # are impossible.
    if result["bp_diastolic"] >= result["bp_systolic"]:
        result["bp_diastolic"] = result["bp_systolic"] - 1.0
    return result


# ── Complication Types & Effects ──
COMPLICATION_TYPES = [
    "hypoxia",
    "hemorrhage",
    "infection",
    "thrombosis",
    "cardiac_arrhythmia",
    "anaphylaxis",
    "nerve_injury",
    "fluid_overload",
]

COMPLICATION_VITAL_EFFECTS: Dict[str, Dict[str, float]] = {
    "hypoxia":             {"spo2": -12.0, "heart_rate": +15.0, "respiratory_rate": +8.0, "bp_systolic": -5.0},
    "hemorrhage":          {"heart_rate": +35.0, "bp_systolic": -30.0, "bp_diastolic": -20.0, "spo2": -3.0, "respiratory_rate": +6.0},
    "infection":           {"temperature": +2.0, "heart_rate": +12.0, "bp_systolic": -8.0},
    "thrombosis":          {"heart_rate": +10.0, "bp_systolic": -15.0, "spo2": -6.0, "respiratory_rate": +4.0},
    "cardiac_arrhythmia":  {"heart_rate": +40.0, "bp_systolic": -25.0, "bp_diastolic": -15.0, "spo2": -5.0},
    "anaphylaxis":         {"heart_rate": +30.0, "bp_systolic": -40.0, "bp_diastolic": -25.0, "spo2": -10.0, "respiratory_rate": +12.0},
    "nerve_injury":        {"heart_rate": +12.0, "bp_systolic": +10.0, "respiratory_rate": +3.0},
    "fluid_overload":      {"spo2": -8.0, "heart_rate": +8.0, "bp_systolic": +10.0, "respiratory_rate": +5.0},
}

# ── Decision Archetypes ──
DECISION_ARCHETYPES = [
    "AIRWAY_STABILITY",
    "HEMODYNAMIC_CONTROL",
    "BLEEDING_CONTROL",
    "INFECTION_MANAGEMENT",
    "PAIN_MANAGEMENT",
    "DIAGNOSTIC_STEP",
    "SURGICAL_DECISION",
    "POST_OP_MONITORING",
]

ARCHETYPE_COMPLICATION_MAP: Dict[str, List[str]] = {
    "AIRWAY_STABILITY":     ["hypoxia", "anaphylaxis"],
    "HEMODYNAMIC_CONTROL":  ["hemorrhage", "cardiac_arrhythmia", "fluid_overload", "anaphylaxis"],
    "BLEEDING_CONTROL":     ["hemorrhage"],
    "INFECTION_MANAGEMENT": ["infection"],
    "PAIN_MANAGEMENT":      ["nerve_injury"],
    "DIAGNOSTIC_STEP":      ["infection", "thrombosis", "nerve_injury"],
    "SURGICAL_DECISION":    ["hemorrhage", "nerve_injury", "thrombosis"],
    "POST_OP_MONITORING":   ["infection", "thrombosis", "fluid_overload"],
}

# ── Procedure-phase awareness ──
# Each procedure phase falls into one of three buckets (pre-op / intra-op /
# post-op), and each decision archetype is only offered in the buckets where its
# interventions make clinical sense (e.g. BLEEDING_CONTROL — cautery/ligation —
# only while the patient is still in the OR). The engine prefers phase-eligible
# archetypes so decisions match where the surgery actually is, falling back to
# any eligible archetype so a complication is always resolvable.
PHASE_BUCKETS = ["pre_op", "intra_op", "post_op"]

_PHASE_PRE_KEYWORDS = ["intake", "pre-op", "preop", "evaluation", "positioning",
                       "stabilization", "induction", "anesthesia", "consult",
                       "planning", "template"]
_PHASE_POST_KEYWORDS = ["post-op", "postop", "debrief", "icu", "recovery"]


def classify_phase(name: str) -> str:
    """Map a procedure phase NAME to a bucket. Phases that aren't recognizably
    pre- or post-op are treated as intra-op (the default operating room state)."""
    n = (name or "").lower()
    for kw in _PHASE_POST_KEYWORDS:
        if kw in n:
            return "post_op"
    for kw in _PHASE_PRE_KEYWORDS:
        if kw in n:
            return "pre_op"
    return "intra_op"


ARCHETYPE_PHASE_BUCKETS: Dict[str, List[str]] = {
    "AIRWAY_STABILITY":     ["pre_op", "intra_op", "post_op"],
    "HEMODYNAMIC_CONTROL":  ["intra_op", "post_op"],
    "BLEEDING_CONTROL":     ["intra_op"],
    "INFECTION_MANAGEMENT": ["intra_op", "post_op"],
    "PAIN_MANAGEMENT":      ["intra_op", "post_op"],
    "DIAGNOSTIC_STEP":      ["pre_op", "intra_op", "post_op"],
    "SURGICAL_DECISION":    ["intra_op"],
    "POST_OP_MONITORING":   ["post_op"],
}

# Per-OPTION phase overrides on top of the archetype's buckets. Options not
# listed inherit their archetype's buckets. Treating options are NEVER filtered
# (a complication must always stay resolvable) — this governs the DECOY pool
# only, so e.g. "Surgical exploration" never appears as a decoy during Post-Op
# and "CT imaging" is not offered mid-case.
OPTION_PHASE_OVERRIDES: Dict[str, List[str]] = {
    "exploration": ["intra_op"],        # surgical exploration only in the OR
    "imaging":     ["pre_op", "post_op"],  # no intra-operative imaging
}


ESCALATION_PHASES = [
    "stable_workup",
    "complication_risk",
    "active_complication",
    "crisis_management",
    "recovery_or_failure",
]

ESCALATION_LABELS: Dict[str, str] = {
    "stable_workup": "Stable Workup",
    "complication_risk": "Complication Risk",
    "active_complication": "Active Complication",
    "crisis_management": "Crisis Management",
    "recovery_or_failure": "Recovery / Failure",
}

ARCHETYPE_PROMPTS: Dict[str, Dict[str, str]] = {
    "AIRWAY_STABILITY": {
        "prompt": "Airway stability is compromised. What intervention do you choose?",
        "context": "The patient is showing signs of airway difficulty. SpO2 is trending down. You must act to secure the airway.",
    },
    "HEMODYNAMIC_CONTROL": {
        "prompt": "Hemodynamic instability detected. How do you respond?",
        "context": "Blood pressure and heart rate are outside safe parameters. Hemodynamic control is critical.",
    },
    "BLEEDING_CONTROL": {
        "prompt": "Active bleeding identified. What is your next step?",
        "context": "Surgical bleeding is observed. Immediate hemostasis is required to prevent exsanguination.",
    },
    "INFECTION_MANAGEMENT": {
        "prompt": "Signs of infection are present. What do you do?",
        "context": "The patient is developing signs of surgical site infection or sepsis. Timely intervention is essential.",
    },
    "PAIN_MANAGEMENT": {
        "prompt": "The patient is in significant pain. How do you manage it?",
        "context": "Pain levels are elevated and may interfere with recovery. Choose an appropriate analgesic strategy.",
    },
    "DIAGNOSTIC_STEP": {
        "prompt": "A diagnostic decision is needed. What do you order?",
        "context": "The clinical picture is unclear. You need more information before proceeding. Choose the right diagnostic step.",
    },
    "SURGICAL_DECISION": {
        "prompt": "A critical surgical decision point. Which approach do you take?",
        "context": "You've reached a key surgical decision point. The wrong choice could lead to serious complications.",
    },
    "POST_OP_MONITORING": {
        "prompt": "Post-operative monitoring required. What do you check first?",
        "context": "The patient is in the post-operative period. Early detection of complications saves lives.",
    },
}

ARCHETYPE_INTERVENTIONS: Dict[str, List[Dict[str, Any]]] = {
    "AIRWAY_STABILITY": [
        {
            "id": "intubate",
            "label": "Intubate & secure airway",
            "treats": ["hypoxia", "anaphylaxis"],
            "vitalsEffect": {"spo2": +8, "heart_rate": -3, "respiratory_rate": -4},
            "riskIfWrong": {"spo2": -5, "heart_rate": +10},
            "correctFeedback": "Airway secured successfully. SpO2 improving.",
            "wrongFeedback": "Intubation was unnecessary — caused mild trauma and temporary desaturation.",
        },
        {
            "id": "oxygen_therapy",
            "label": "Administer supplemental O₂",
            "treats": ["hypoxia"],
            "vitalsEffect": {"spo2": +4, "respiratory_rate": -2},
            "riskIfWrong": {"spo2": -2},
            "correctFeedback": "Oxygen therapy effective. Saturation improving.",
            "wrongFeedback": "O₂ alone is insufficient for this severity. Delayed proper intervention.",
        },
        {
            "id": "cricothyroidotomy",
            "label": "Emergency cricothyroidotomy",
            "treats": ["anaphylaxis", "hypoxia"],
            "vitalsEffect": {"spo2": +12, "heart_rate": -5},
            "riskIfWrong": {"spo2": -8, "heart_rate": +15},
            "correctFeedback": "Surgical airway established. Patient stabilized.",
            "wrongFeedback": "Cricothyroidotomy was overly aggressive. Unnecessary surgical trauma inflicted.",
        },
        {
            "id": "call_anesthesia",
            "label": "Call for anesthesia support",
            "treats": [],
            "vitalsEffect": {},
            "riskIfWrong": {"spo2": -4, "heart_rate": +5, "respiratory_rate": +2},
            "correctFeedback": "Anesthesia team consulted. Additional expertise on the way.",
            "wrongFeedback": "Waiting for anesthesia support delayed critical intervention.",
        },
    ],
    "HEMODYNAMIC_CONTROL": [
        {
            "id": "fluid_resuscitation",
            "label": "IV fluid bolus",
            "treats": ["hemorrhage"],
            "vitalsEffect": {"bp_systolic": +10, "heart_rate": -8},
            "riskIfWrong": {"bp_systolic": -5, "heart_rate": +5},
            "correctFeedback": "Fluid resuscitation restoring intravascular volume. BP stabilizing.",
            "wrongFeedback": "Fluid bolus in a volume-overloaded patient worsens pulmonary edema.",
        },
        {
            "id": "vasopressor",
            "label": "Start vasopressor drip",
            "treats": [],
            "vitalsEffect": {"bp_systolic": +15, "heart_rate": +5},
            "riskIfWrong": {"heart_rate": +20, "bp_systolic": +25},
            "correctFeedback": "Vasopressor support effective. Perfusion improving.",
            "wrongFeedback": "Vasopressors do not control hemorrhage or fix an arrhythmia — surgical control and rhythm management do.",
        },
        {
            "id": "blood_transfusion",
            "label": "Transfuse packed RBCs",
            "treats": ["hemorrhage"],
            "vitalsEffect": {"bp_systolic": +12, "heart_rate": -10, "spo2": +2},
            "riskIfWrong": {"bp_systolic": -3, "temperature": +0.5},
            "correctFeedback": "Transfusion restoring oxygen-carrying capacity. Vitals improving.",
            "wrongFeedback": "Transfusion was not indicated. Risk of transfusion reaction.",
        },
        {
            "id": "cardioversion",
            "label": "Electrical cardioversion",
            "treats": ["cardiac_arrhythmia"],
            "vitalsEffect": {"heart_rate": -30, "bp_systolic": +10},
            "riskIfWrong": {"heart_rate": +15, "bp_systolic": -10},
            "correctFeedback": "Sinus rhythm restored. Hemodynamics stabilizing.",
            "wrongFeedback": "Cardioversion was not the right intervention. Cardiac irritability increased.",
        },
        {
            "id": "diuretic",
            "label": "IV furosemide (diuresis)",
            "treats": ["fluid_overload"],
            "vitalsEffect": {"bp_systolic": -6, "heart_rate": -4, "spo2": +6, "respiratory_rate": -3},
            "riskIfWrong": {"bp_systolic": -12, "heart_rate": -8},
            "correctFeedback": "Diuresis offloads the lungs. SpO2 and work of breathing improving.",
            "wrongFeedback": "Diuresis in a volume-depleted patient caused hypotension.",
        },
        {
            "id": "epinephrine",
            "label": "Epinephrine 0.5 mg IM",
            "treats": ["anaphylaxis"],
            "vitalsEffect": {"bp_systolic": +18, "heart_rate": +8, "spo2": +6, "respiratory_rate": -4},
            "riskIfWrong": {"heart_rate": +35, "bp_systolic": +30},
            "correctFeedback": "Epinephrine reverses anaphylactic vasodilation and bronchospasm.",
            "wrongFeedback": "Epinephrine without anaphylaxis caused dangerous tachycardia and hypertension.",
        },
    ],
    "BLEEDING_CONTROL": [
        {
            "id": "cautery",
            "label": "Electrocautery of bleeders",
            "treats": ["hemorrhage"],
            "vitalsEffect": {"bp_systolic": +5, "heart_rate": -5},
            "riskIfWrong": {"temperature": +0.3},
            "correctFeedback": "Bleeders cauterized. Surgical field is dry.",
            "wrongFeedback": "Cautery caused thermal spread to adjacent tissue.",
        },
        {
            "id": "ligation",
            "label": "Suture ligation of vessel",
            "treats": ["hemorrhage"],
            "vitalsEffect": {"bp_systolic": +8, "heart_rate": -8},
            "riskIfWrong": {"bp_systolic": -5},
            "correctFeedback": "Vessel ligated securely. Hemostasis achieved.",
            "wrongFeedback": "Ligation was unnecessary — no active bleeding vessel found.",
        },
        {
            "id": "packing",
            "label": "Pack wound temporarily",
            "treats": ["hemorrhage"],
            "vitalsEffect": {"bp_systolic": +3, "heart_rate": -3},
            "riskIfWrong": {"temperature": +0.5},
            "correctFeedback": "Packing applied. Bleeding controlled for now.",
            "wrongFeedback": "Packing introduced without active hemorrhage — infection risk increased.",
        },
        {
            "id": "observe_hemostasis",
            "label": "Observe for hemostasis",
            "treats": [],
            "vitalsEffect": {},
            "riskIfWrong": {"bp_systolic": -8, "heart_rate": +8},
            "correctFeedback": "Observation confirms hemostasis. No active bleeding.",
            "wrongFeedback": "Observation delayed intervention. Bleeding worsened.",
        },
    ],
    "INFECTION_MANAGEMENT": [
        {
            "id": "antibiotics_iv",
            "label": "IV broad-spectrum antibiotics",
            "treats": ["infection"],
            "vitalsEffect": {"temperature": -0.8, "heart_rate": -5},
            "riskIfWrong": {"temperature": +0.3},
            "correctFeedback": "Antibiotics initiated. Inflammatory markers should begin improving.",
            "wrongFeedback": "Antibiotics given without clear indication. Unnecessary exposure.",
        },
        {
            "id": "wound_irrigation",
            "label": "Irrigate & debride wound",
            "treats": ["infection"],
            "vitalsEffect": {"temperature": -0.5, "heart_rate": -3},
            "riskIfWrong": {"bp_systolic": -5},
            "correctFeedback": "Wound thoroughly irrigated. Source control achieved.",
            "wrongFeedback": "Irrigation disrupted a clean wound bed unnecessarily.",
        },
        {
            "id": "source_control",
            "label": "Surgical source control",
            "treats": ["infection"],
            "vitalsEffect": {"temperature": -1.2, "heart_rate": -8, "bp_systolic": +5},
            "riskIfWrong": {"bp_systolic": -10, "heart_rate": +10},
            "correctFeedback": "Source control obtained. Sepsis should begin resolving.",
            "wrongFeedback": "Surgical exploration was premature. No infectious source found.",
        },
        {
            "id": "cultures_first",
            "label": "Draw cultures before treating",
            "treats": [],
            "vitalsEffect": {},
            "riskIfWrong": {"temperature": +0.5, "heart_rate": +5},
            "correctFeedback": "Cultures drawn. Targeted therapy can begin once sensitivities return.",
            "wrongFeedback": "Delaying treatment for cultures allowed infection to progress.",
        },
    ],
    "PAIN_MANAGEMENT": [
        {
            "id": "iv_opioid",
            "label": "IV opioid analgesic",
            "treats": ["nerve_injury"],
            "vitalsEffect": {"heart_rate": -8, "bp_systolic": -3, "respiratory_rate": -2},
            "riskIfWrong": {"spo2": -3, "respiratory_rate": -4},
            "correctFeedback": "Pain controlled. Patient comfortable and vitals stabilizing.",
            "wrongFeedback": "Opioid caused respiratory depression. SpO2 dropping.",
        },
        {
            "id": "regional_block",
            "label": "Regional nerve block",
            "treats": ["nerve_injury"],
            "vitalsEffect": {"heart_rate": -10, "bp_systolic": -5},
            "riskIfWrong": {"heart_rate": +5, "bp_systolic": -8},
            "correctFeedback": "Regional block effective. Pain well-controlled with minimal systemic effect.",
            "wrongFeedback": "Block caused unintended sympathetic blockade. Hypotension developing.",
        },
        {
            "id": "nsaid",
            "label": "IV NSAID (ketorolac)",
            "treats": ["nerve_injury"],
            "vitalsEffect": {"heart_rate": -4, "temperature": -0.2},
            "riskIfWrong": {"bp_systolic": +5},
            "correctFeedback": "NSAID providing adjunct pain relief. Anti-inflammatory effect helpful.",
            "wrongFeedback": "NSAID contraindicated in this scenario. May worsen bleeding risk.",
        },
        {
            "id": "non_pharmacologic",
            "label": "Non-pharmacologic pain management",
            "treats": [],
            "vitalsEffect": {},
            "riskIfWrong": {"heart_rate": +5},
            "correctFeedback": "Non-pharmacologic measures adequate for current pain level.",
            "wrongFeedback": "Pain too severe for non-pharmacologic measures alone. Patient distress increasing.",
        },
    ],
    "DIAGNOSTIC_STEP": [
        {
            "id": "imaging",
            "label": "Order imaging (CT/X-ray)",
            "treats": ["thrombosis", "nerve_injury"],
            "vitalsEffect": {},
            "riskIfWrong": {"heart_rate": +3},
            "correctFeedback": "Imaging reveals the key finding. Diagnosis clarified.",
            "wrongFeedback": "Imaging was non-contributory. Time and resources wasted.",
        },
        {
            "id": "labs",
            "label": "Draw stat labs (ABG, CBC, CMP)",
            "treats": ["infection", "thrombosis"],
            "vitalsEffect": {},
            "riskIfWrong": {"heart_rate": +2},
            "correctFeedback": "Lab results confirm the clinical suspicion. Appropriate treatment can begin.",
            "wrongFeedback": "Labs were unnecessary at this point. No actionable findings.",
        },
        {
            "id": "exploration",
            "label": "Surgical exploration",
            "treats": ["infection", "nerve_injury"],
            "vitalsEffect": {"heart_rate": +5, "bp_systolic": -3},
            "riskIfWrong": {"bp_systolic": -8, "heart_rate": +10},
            "correctFeedback": "Exploration reveals the problem. Direct visualization confirms diagnosis.",
            "wrongFeedback": "Exploration was premature. No pathology found, and surgical trauma added.",
        },
        {
            "id": "consult_specialist",
            "label": "Consult specialist for opinion",
            "treats": [],
            "vitalsEffect": {},
            "riskIfWrong": {"heart_rate": +2},
            "correctFeedback": "Specialist input clarifies the diagnosis. Correct pathway identified.",
            "wrongFeedback": "Waiting for consult delayed critical decision-making.",
        },
    ],
    "SURGICAL_DECISION": [
        {
            "id": "proceed",
            "label": "Proceed with planned approach",
            "treats": ["hemorrhage", "nerve_injury"],
            "vitalsEffect": {"heart_rate": +3},
            "riskIfWrong": {"heart_rate": +8, "bp_systolic": -5},
            "correctFeedback": "Planned approach is appropriate. Proceeding safely.",
            "wrongFeedback": "The planned approach is not safe given current conditions. Complication risk rising.",
        },
        {
            "id": "modify",
            "label": "Modify surgical approach",
            "treats": ["thrombosis", "nerve_injury"],
            "vitalsEffect": {"heart_rate": -2},
            "riskIfWrong": {"heart_rate": +5, "bp_systolic": -3},
            "correctFeedback": "Modified approach avoids the danger zone. Good surgical judgment.",
            "wrongFeedback": "Modification was unnecessary. The original approach was safer.",
        },
        {
            "id": "abort",
            "label": "Abort / staged procedure",
            "treats": ["hemorrhage", "thrombosis"],
            "vitalsEffect": {"heart_rate": -5, "bp_systolic": +5},
            "riskIfWrong": {"heart_rate": +10, "bp_systolic": -5},
            "correctFeedback": "Correct call to abort. Patient safety prioritized over completing the case.",
            "wrongFeedback": "Aborting was premature. The case could have been completed safely.",
        },
        {
            "id": "request_assistance",
            "label": "Request senior surgeon assistance",
            "treats": [],
            "vitalsEffect": {},
            "riskIfWrong": {"heart_rate": +5},
            "correctFeedback": "Senior assistance improves outcome. Second opinion confirms approach.",
            "wrongFeedback": "Waiting for assistance consumed critical time.",
        },
    ],
    "POST_OP_MONITORING": [
        {
            "id": "vitals_check",
            "label": "Close vitals monitoring (q15min)",
            "treats": ["infection", "fluid_overload"],
            "vitalsEffect": {},
            "riskIfWrong": {"heart_rate": +5},
            "correctFeedback": "Close monitoring detected the change early. Intervention initiated promptly.",
            "wrongFeedback": "Over-monitoring is tying up resources. Standard frequency is sufficient.",
        },
        {
            "id": "doppler",
            "label": "Doppler ultrasound for DVT",
            "treats": ["thrombosis"],
            "vitalsEffect": {},
            "riskIfWrong": {"heart_rate": +3},
            "correctFeedback": "Doppler caught the clot early. Anticoagulation started.",
            "wrongFeedback": "Doppler was negative. Unnecessary study performed.",
        },
        {
            "id": "anticoagulation",
            "label": "Start IV heparin (anticoagulation)",
            "treats": ["thrombosis"],
            "vitalsEffect": {"spo2": +2, "heart_rate": -3},
            "riskIfWrong": {"bp_systolic": -10},
            "correctFeedback": "Anticoagulation halts clot propagation. Clinical status stabilizing.",
            "wrongFeedback": "Full anticoagulation in a bleeding-risk patient caused hemorrhage.",
        },
        {
            "id": "serial_labs",
            "label": "Serial labs (q6h Hgb, lactate)",
            "treats": ["infection", "fluid_overload", "hemorrhage"],
            "vitalsEffect": {},
            "riskIfWrong": {"temperature": +0.2},
            "correctFeedback": "Serial labs trending in the right direction. Continue current management.",
            "wrongFeedback": "Serial labs show no change. Unnecessary blood draws.",
        },
        {
            "id": "icu_transfer",
            "label": "Transfer to ICU for monitoring",
            "treats": [],
            "vitalsEffect": {},
            "riskIfWrong": {"heart_rate": +3},
            "correctFeedback": "ICU transfer appropriate for this risk level. Close observation initiated.",
            "wrongFeedback": "ICU transfer was unnecessary. Floor monitoring is sufficient.",
        },
    ],
}

# ── Risk Profiles ──
# deterioration_rate scales how fast the patient's physiology fails over the
# course of the case: vitals trend downward each engine tick, the decline
# accelerates the sicker the patient gets, and complications spawn on their own
# as vitals deteriorate — the trainee must actively tend to the patient.
RISK_PROFILES: Dict[str, Dict[str, float]] = {
    "low":       {"base_complication_chance": 0.15, "crisis_threshold_factor": 1.5, "recovery_speed": 0.8, "deterioration_rate": 0.45},
    "moderate":  {"base_complication_chance": 0.25, "crisis_threshold_factor": 1.0, "recovery_speed": 0.5, "deterioration_rate": 0.8},
    "high":      {"base_complication_chance": 0.35, "crisis_threshold_factor": 0.7, "recovery_speed": 0.3, "deterioration_rate": 1.6},
    "critical":  {"base_complication_chance": 0.45, "crisis_threshold_factor": 0.5, "recovery_speed": 0.4, "deterioration_rate": 2.0},
}


def build_escalation(total_ticks: int, curve: str) -> Dict[str, Any]:
    ratios = {
        "mild":       {"p1": 0.25, "p2": 0.15, "p3": 0.25, "p4": 0.20, "p5": 0.15},
        "moderate":   {"p1": 0.20, "p2": 0.15, "p3": 0.25, "p4": 0.25, "p5": 0.15},
        "aggressive": {"p1": 0.12, "p2": 0.13, "p3": 0.25, "p4": 0.30, "p5": 0.20},
    }[curve]

    def r(pct: float) -> int:
        return round(total_ticks * pct)

    def t(start: int, end: int) -> list[int]:
        return [max(1, start), min(total_ticks, end)]

    cursor = 0
    p1e = cursor + r(ratios["p1"]); cursor = p1e
    p2e = cursor + r(ratios["p2"]); cursor = p2e
    p3e = cursor + r(ratios["p3"]); cursor = p3e
    p4e = cursor + r(ratios["p4"]); cursor = p4e

    return {
        "phase1": {"tickRange": t(1, p1e), "label": "Stable Workup"},
        "phase2": {"tickRange": t(p1e + 1, p2e), "label": "Complication Risk"},
        "phase3": {"tickRange": t(p2e + 1, p3e), "label": "Active Complication"},
        "phase4": {"tickRange": t(p3e + 1, p4e), "label": "Crisis Management"},
        "phase5": {"tickRange": t(p4e + 1, total_ticks), "label": "Recovery / Failure"},
    }


# ════════════════════════════════════════════════════
#  ALL 31 PROCEDURES
# ════════════════════════════════════════════════════

ALL_PROCEDURES: List[Dict[str, Any]] = [
    # ── BEGINNER (4) ──
    {
        "id": "appendectomy",
        "name": "Appendectomy",
        "category": "beginner",
        "specialty": "General Surgery",
        "description": "Emergency removal of an inflamed appendix. Watch for perforation and infection.",
        "patient": {
            "name": "Marcus T.", "age": 28, "sex": "Male", "weight": "95 kg", "bloodType": "O+",
            "admission": "Acute right lower quadrant pain, rebound tenderness, low-grade fever 100.0°F",
            "mood": "Anxious", "comorbidities": ["obese"],
            "baselineVitals": {"spo2": 97, "heart_rate": 110, "bp_systolic": 95, "bp_diastolic": 65, "temperature": 37.8, "respiratory_rate": 22},
        },
        "initialState": {
            "vitals_override": {"heart_rate": 110, "bp_systolic": 95},
            "riskProfile": RISK_PROFILES["moderate"],
        },
        "complicationWeights": {"infection": 5, "hemorrhage": 2, "hypoxia": 1},
        "allowedComplications": ["infection", "hemorrhage", "hypoxia"],
        "decisionArchetypes": ["AIRWAY_STABILITY", "BLEEDING_CONTROL", "INFECTION_MANAGEMENT"],
        "escalationCurve": build_escalation(30, "moderate"),
        "phases": [
            {"id": 1, "name": "Patient Intake", "icon": "🩺", "short": "Intake"},
            {"id": 2, "name": "Pre-Op Planning", "icon": "📋", "short": "Pre-Op"},
            {"id": 3, "name": "Incision & Access", "icon": "🔪", "short": "Incision"},
            {"id": 4, "name": "Core Procedure", "icon": "⚕️", "short": "Procedure"},
            {"id": 5, "name": "Closing", "icon": "🪡", "short": "Closing"},
            {"id": 6, "name": "Post-Op", "icon": "📊", "short": "Post-Op"},
        ],
        "totalTicks": 30,
    },
    {
        "id": "inguinal-hernia",
        "name": "Inguinal Hernia Repair",
        "category": "beginner",
        "specialty": "General Surgery",
        "description": "Elective repair of a reducible inguinal hernia with mesh placement.",
        "patient": {
            "name": "Michael R.", "age": 45, "sex": "Male", "weight": "82 kg", "bloodType": "O+",
            "admission": "Right groin bulge for 6 months, fully reducible",
            "mood": "Anxious", "comorbidities": [],
            "baselineVitals": {"spo2": 98, "heart_rate": 72, "bp_systolic": 120, "bp_diastolic": 80, "temperature": 37.0, "respiratory_rate": 16},
        },
        "initialState": {"vitals_override": {}, "riskProfile": RISK_PROFILES["low"]},
        "complicationWeights": {"hemorrhage": 3, "nerve_injury": 2, "infection": 1},
        "allowedComplications": ["hemorrhage", "nerve_injury", "infection"],
        "decisionArchetypes": ["SURGICAL_DECISION", "BLEEDING_CONTROL"],
        "escalationCurve": build_escalation(30, "mild"),
        "phases": [
            {"id": 1, "name": "Patient Intake", "icon": "🩺", "short": "Intake"},
            {"id": 2, "name": "Pre-Op Planning", "icon": "📋", "short": "Pre-Op"},
            {"id": 3, "name": "Incision & Dissection", "icon": "🔪", "short": "Dissection"},
            {"id": 4, "name": "Mesh Placement", "icon": "🧱", "short": "Mesh"},
            {"id": 5, "name": "Closure", "icon": "🪡", "short": "Closing"},
            {"id": 6, "name": "Post-Op", "icon": "📊", "short": "Post-Op"},
        ],
        "totalTicks": 30,
    },
    {
        "id": "thyroidectomy",
        "name": "Thyroidectomy",
        "category": "beginner",
        "specialty": "ENT",
        "description": "Total thyroidectomy for follicular neoplasm. Airway and RLN are critical.",
        "patient": {
            "name": "Emily R.", "age": 38, "sex": "Female", "weight": "68 kg", "bloodType": "A+",
            "admission": "Palpable thyroid nodule, Bethesda IV follicular neoplasm",
            "mood": "Anxious but well-informed", "comorbidities": [],
            "baselineVitals": {"spo2": 98, "heart_rate": 72, "bp_systolic": 120, "bp_diastolic": 80, "temperature": 37.0, "respiratory_rate": 16},
        },
        "initialState": {"vitals_override": {}, "riskProfile": RISK_PROFILES["low"]},
        "complicationWeights": {"hypoxia": 4, "nerve_injury": 3, "hemorrhage": 2},
        "allowedComplications": ["hypoxia", "nerve_injury", "hemorrhage"],
        "decisionArchetypes": ["AIRWAY_STABILITY", "DIAGNOSTIC_STEP"],
        "escalationCurve": build_escalation(30, "mild"),
        "phases": [
            {"id": 1, "name": "Patient Intake", "icon": "🩺", "short": "Intake"},
            {"id": 2, "name": "Pre-Op Planning", "icon": "📋", "short": "Pre-Op"},
            {"id": 3, "name": "Incision & Access", "icon": "🔪", "short": "Incision"},
            {"id": 4, "name": "Core Procedure", "icon": "⚕️", "short": "Procedure"},
            {"id": 5, "name": "Closing", "icon": "🪡", "short": "Closing"},
            {"id": 6, "name": "Post-Op", "icon": "📊", "short": "Post-Op"},
        ],
        "totalTicks": 30,
    },
    {
        "id": "carpal-tunnel-release",
        "name": "Carpal Tunnel Release",
        "category": "beginner",
        "specialty": "Orthopedic",
        "description": "Open carpal tunnel release for median nerve decompression at the wrist.",
        "patient": {
            "name": "Linda K.", "age": 52, "sex": "Female", "weight": "65 kg", "bloodType": "B+",
            "admission": "Numbness and tingling in thumb, index, and middle fingers for 8 months",
            "mood": "Relieved", "comorbidities": [],
            "baselineVitals": {"spo2": 98, "heart_rate": 72, "bp_systolic": 120, "bp_diastolic": 80, "temperature": 37.0, "respiratory_rate": 16},
        },
        "initialState": {"vitals_override": {}, "riskProfile": RISK_PROFILES["low"]},
        "complicationWeights": {"nerve_injury": 3, "infection": 1},
        "allowedComplications": ["nerve_injury", "infection"],
        "decisionArchetypes": ["SURGICAL_DECISION", "PAIN_MANAGEMENT"],
        "escalationCurve": build_escalation(25, "mild"),
        "phases": [
            {"id": 1, "name": "Patient Intake", "icon": "🩺", "short": "Intake"},
            {"id": 2, "name": "Pre-Op", "icon": "📋", "short": "Pre-Op"},
            {"id": 3, "name": "Incision", "icon": "🔪", "short": "Incision"},
            {"id": 4, "name": "Release", "icon": "⚕️", "short": "Release"},
            {"id": 5, "name": "Closing", "icon": "🪡", "short": "Closing"},
            {"id": 6, "name": "Post-Op", "icon": "📊", "short": "Post-Op"},
        ],
        "totalTicks": 25,
    },

    # ── INTERMEDIATE (15) ──
    {
        "id": "cholecystectomy",
        "name": "Cholecystectomy",
        "category": "intermediate",
        "specialty": "General Surgery",
        "description": "Laparoscopic removal of gallbladder. Critical view of safety is essential.",
        "patient": {
            "name": "Sarah J.", "age": 42, "sex": "Female", "weight": "78 kg", "bloodType": "B+",
            "admission": "Right upper quadrant pain, Murphy's sign positive, history of gallstones",
            "mood": "Anxious but cooperative", "comorbidities": ["obese"],
            "baselineVitals": {"spo2": 97, "heart_rate": 80, "bp_systolic": 120, "bp_diastolic": 80, "temperature": 37.0, "respiratory_rate": 16},
        },
        "initialState": {"vitals_override": {"heart_rate": 80}, "riskProfile": RISK_PROFILES["moderate"]},
        "complicationWeights": {"infection": 4, "hemorrhage": 3, "hypoxia": 2},
        "allowedComplications": ["infection", "hemorrhage", "hypoxia"],
        "decisionArchetypes": ["INFECTION_MANAGEMENT", "DIAGNOSTIC_STEP"],
        "escalationCurve": build_escalation(35, "moderate"),
        "phases": [
            {"id": 1, "name": "Evaluation", "icon": "🩺", "short": "Intake"},
            {"id": 2, "name": "Stabilization", "icon": "📋", "short": "Pre-Op"},
            {"id": 3, "name": "Laparoscopic Entry", "icon": "🔪", "short": "Access"},
            {"id": 4, "name": "Gallbladder Removal", "icon": "⚕️", "short": "Removal"},
            {"id": 5, "name": "Hemostasis & Closure", "icon": "🪡", "short": "Closing"},
            {"id": 6, "name": "Post-Op Debrief", "icon": "📊", "short": "Post-Op"},
        ],
        "totalTicks": 35,
    },
    {
        "id": "acl-reconstruction",
        "name": "ACL Reconstruction",
        "category": "intermediate",
        "specialty": "Orthopedic",
        "description": "Arthroscopic anterior cruciate ligament reconstruction with graft fixation.",
        "patient": {
            "name": "Jordan K.", "age": 22, "sex": "Male", "weight": "82 kg", "bloodType": "O+",
            "admission": "Knee injury during soccer, positive Lachman test",
            "mood": "Determined", "comorbidities": [],
            "baselineVitals": {"spo2": 98, "heart_rate": 72, "bp_systolic": 95, "bp_diastolic": 64, "temperature": 37.0, "respiratory_rate": 16},
        },
        "initialState": {"vitals_override": {}, "riskProfile": RISK_PROFILES["moderate"]},
        "complicationWeights": {"hemorrhage": 3, "nerve_injury": 2, "infection": 2},
        "allowedComplications": ["hemorrhage", "nerve_injury", "infection"],
        "decisionArchetypes": ["SURGICAL_DECISION", "PAIN_MANAGEMENT"],
        "escalationCurve": build_escalation(30, "moderate"),
        "phases": [
            {"id": 1, "name": "Evaluation", "icon": "🦵", "short": "Exam"},
            {"id": 2, "name": "Access", "icon": "🎥", "short": "Arthroscopy"},
            {"id": 3, "name": "Graft Harvesting", "icon": "✂️", "short": "Graft"},
            {"id": 4, "name": "Tunnel Drilling", "icon": "⚙️", "short": "Drilling"},
            {"id": 5, "name": "Fixation", "icon": "🔩", "short": "Fixation"},
            {"id": 6, "name": "Recovery", "icon": "🏆", "short": "Rehab"},
        ],
        "totalTicks": 30,
    },
    {
        "id": "c-section",
        "name": "Cesarean Section",
        "category": "intermediate",
        "specialty": "OB/GYN",
        "description": "Emergency cesarean delivery for non-reassuring fetal tracing. Dual patient focus.",
        "patient": {
            "name": "Maria L.", "age": 31, "sex": "Female", "weight": "92 kg", "bloodType": "A+",
            "admission": "39 weeks gestation, failure to progress, non-reassuring fetal tracing",
            "mood": "Exhausted but determined", "comorbidities": [],
            "baselineVitals": {"spo2": 98, "heart_rate": 88, "bp_systolic": 90, "bp_diastolic": 60, "temperature": 37.0, "respiratory_rate": 18},
        },
        "initialState": {"vitals_override": {"heart_rate": 88, "bp_systolic": 90, "respiratory_rate": 18}, "riskProfile": RISK_PROFILES["moderate"]},
        "complicationWeights": {"hemorrhage": 5, "hypoxia": 3, "cardiac_arrhythmia": 2},
        "allowedComplications": ["hemorrhage", "hypoxia", "cardiac_arrhythmia"],
        "decisionArchetypes": ["HEMODYNAMIC_CONTROL", "AIRWAY_STABILITY"],
        "escalationCurve": build_escalation(30, "moderate"),
        "phases": [
            {"id": 1, "name": "Evaluation", "icon": "🤰", "short": "Labor"},
            {"id": 2, "name": "Intake", "icon": "💉", "short": "Epidural"},
            {"id": 3, "name": "Abdominal Entry", "icon": "⚗️", "short": "Pfannenstiel"},
            {"id": 4, "name": "Delivery", "icon": "👶", "short": "Delivery"},
            {"id": 5, "name": "Closure", "icon": "🪡", "short": "Repair"},
            {"id": 6, "name": "Post-Partum", "icon": "👩‍🍼", "short": "Recovery"},
        ],
        "totalTicks": 30,
    },
    {
        "id": "total-knee-replacement",
        "name": "Total Knee Replacement",
        "category": "intermediate",
        "specialty": "Orthopedic",
        "description": "Total knee arthroplasty for severe osteoarthritis with cemented components.",
        "patient": {
            "name": "Evelyn W.", "age": 68, "sex": "Female", "weight": "74 kg", "bloodType": "A-",
            "admission": "Severe right knee osteoarthritis, bone-on-bone medial joint space",
            "mood": "Determined to walk again", "comorbidities": ["hypertension", "diabetes"],
            "baselineVitals": {"spo2": 97, "heart_rate": 82, "bp_systolic": 92, "bp_diastolic": 62, "temperature": 37.0, "respiratory_rate": 16},
        },
        "initialState": {"vitals_override": {"heart_rate": 82, "bp_systolic": 92}, "riskProfile": RISK_PROFILES["moderate"]},
        "complicationWeights": {"thrombosis": 5, "infection": 3, "nerve_injury": 2},
        "allowedComplications": ["hemorrhage", "thrombosis", "infection", "nerve_injury"],
        "decisionArchetypes": ["PAIN_MANAGEMENT", "POST_OP_MONITORING"],
        "escalationCurve": build_escalation(35, "moderate"),
        "phases": [
            {"id": 1, "name": "Consultation", "icon": "📐", "short": "Template"},
            {"id": 2, "name": "Approach", "icon": "🔪", "short": "Entry"},
            {"id": 3, "name": "Osteotomy", "icon": "🪚", "short": "Cuts"},
            {"id": 4, "name": "Trialing", "icon": "👟", "short": "Sizing"},
            {"id": 5, "name": "Fixation", "icon": "🧱", "short": "Cement"},
            {"id": 6, "name": "Closure", "icon": "🪡", "short": "Closing"},
        ],
        "totalTicks": 35,
    },
    {
        "id": "total-hysterectomy",
        "name": "Total Hysterectomy",
        "category": "intermediate",
        "specialty": "OB/GYN",
        "description": "Total abdominal hysterectomy for fibroids. Ureter and vessel identification critical.",
        "patient": {
            "name": "Patricia M.", "age": 46, "sex": "Female", "weight": "75 kg", "bloodType": "AB+",
            "admission": "Large uterine fibroids causing menorrhagia and anemia",
            "mood": "Ready", "comorbidities": [],
            "baselineVitals": {"spo2": 98, "heart_rate": 80, "bp_systolic": 95, "bp_diastolic": 64, "temperature": 37.0, "respiratory_rate": 16},
        },
        "initialState": {"vitals_override": {}, "riskProfile": RISK_PROFILES["moderate"]},
        "complicationWeights": {"hemorrhage": 5, "infection": 3, "nerve_injury": 2},
        "allowedComplications": ["hemorrhage", "infection", "nerve_injury"],
        "decisionArchetypes": ["HEMODYNAMIC_CONTROL", "INFECTION_MANAGEMENT"],
        "escalationCurve": build_escalation(30, "moderate"),
        "phases": [
            {"id": 1, "name": "Patient Intake", "icon": "🩺", "short": "Intake"},
            {"id": 2, "name": "Pre-Op", "icon": "📋", "short": "Pre-Op"},
            {"id": 3, "name": "Incision", "icon": "🔪", "short": "Incision"},
            {"id": 4, "name": "Hysterectomy", "icon": "⚕️", "short": "Procedure"},
            {"id": 5, "name": "Closing", "icon": "🪡", "short": "Closing"},
            {"id": 6, "name": "Post-Op", "icon": "📊", "short": "Post-Op"},
        ],
        "totalTicks": 30,
    },
    {
        "id": "sigmoid-colectomy",
        "name": "Sigmoid Colectomy",
        "category": "intermediate",
        "specialty": "General Surgery",
        "description": "Laparoscopic sigmoid colectomy for diverticulitis with abscess. Leak test is critical.",
        "patient": {
            "name": "Robert J.", "age": 58, "sex": "Male", "weight": "88 kg", "bloodType": "A+",
            "admission": "Left lower quadrant pain, fever, CT showing sigmoid diverticulitis with abscess",
            "mood": "Concerned", "comorbidities": ["hypertension", "diabetes"],
            "baselineVitals": {"spo2": 97, "heart_rate": 76, "bp_systolic": 97, "bp_diastolic": 66, "temperature": 37.5, "respiratory_rate": 16},
        },
        "initialState": {"vitals_override": {"heart_rate": 76, "bp_systolic": 97, "temperature": 37.5}, "riskProfile": RISK_PROFILES["moderate"]},
        "complicationWeights": {"infection": 5, "hemorrhage": 2, "nerve_injury": 1},
        "allowedComplications": ["infection", "hemorrhage", "nerve_injury"],
        "decisionArchetypes": ["INFECTION_MANAGEMENT", "DIAGNOSTIC_STEP"],
        "escalationCurve": build_escalation(30, "moderate"),
        "phases": [
            {"id": 1, "name": "Patient Intake", "icon": "🩺", "short": "Intake"},
            {"id": 2, "name": "Pre-Op Planning", "icon": "📋", "short": "Pre-Op"},
            {"id": 3, "name": "Incision & Access", "icon": "🔪", "short": "Incision"},
            {"id": 4, "name": "Core Procedure", "icon": "⚕️", "short": "Procedure"},
            {"id": 5, "name": "Closing", "icon": "🪡", "short": "Closing"},
            {"id": 6, "name": "Post-Op", "icon": "📊", "short": "Post-Op"},
        ],
        "totalTicks": 30,
    },
    {
        "id": "lap-cholecystectomy",
        "name": "Laparoscopic Cholecystectomy",
        "category": "intermediate",
        "specialty": "Laparoscopic",
        "description": "Laparoscopic cholecystectomy emphasizing critical view of safety. Bile duct injury risk.",
        "patient": {
            "name": "Dana W.", "age": 42, "sex": "Female", "weight": "78 kg", "bloodType": "B+",
            "admission": "Right upper quadrant pain, Murphy's sign positive, gallstones",
            "mood": "Anxious but cooperative", "comorbidities": ["obese"],
            "baselineVitals": {"spo2": 97, "heart_rate": 80, "bp_systolic": 95, "bp_diastolic": 64, "temperature": 37.0, "respiratory_rate": 16},
        },
        "initialState": {"vitals_override": {"heart_rate": 80}, "riskProfile": RISK_PROFILES["moderate"]},
        "complicationWeights": {"hemorrhage": 3, "infection": 2, "nerve_injury": 2},
        "allowedComplications": ["hemorrhage", "infection", "nerve_injury"],
        "decisionArchetypes": ["DIAGNOSTIC_STEP", "SURGICAL_DECISION"],
        "escalationCurve": build_escalation(35, "moderate"),
        "phases": [
            {"id": 1, "name": "Evaluation", "icon": "🩺", "short": "Intake"},
            {"id": 2, "name": "Stabilization", "icon": "📋", "short": "Pre-Op"},
            {"id": 3, "name": "Laparoscopic Entry", "icon": "🔪", "short": "Access"},
            {"id": 4, "name": "Gallbladder Removal", "icon": "⚕️", "short": "Removal"},
            {"id": 5, "name": "Hemostasis & Closure", "icon": "🪡", "short": "Closing"},
            {"id": 6, "name": "Post-Op Debrief", "icon": "📊", "short": "Post-Op"},
        ],
        "totalTicks": 35,
    },
    {
        "id": "radical-nephrectomy",
        "name": "Radical Nephrectomy",
        "category": "intermediate",
        "specialty": "Urology",
        "description": "Radical nephrectomy for renal cell carcinoma. Vascular control is paramount.",
        "patient": {
            "name": "James H.", "age": 58, "sex": "Male", "weight": "90 kg", "bloodType": "O-",
            "admission": "Right renal mass on imaging, hematuria, weight loss",
            "mood": "Stoic", "comorbidities": ["hypertension"],
            "baselineVitals": {"spo2": 97, "heart_rate": 78, "bp_systolic": 92, "bp_diastolic": 62, "temperature": 37.0, "respiratory_rate": 16},
        },
        "initialState": {"vitals_override": {"bp_systolic": 92}, "riskProfile": RISK_PROFILES["moderate"]},
        "complicationWeights": {"hemorrhage": 6, "cardiac_arrhythmia": 2, "infection": 2},
        "allowedComplications": ["hemorrhage", "cardiac_arrhythmia", "infection"],
        "decisionArchetypes": ["HEMODYNAMIC_CONTROL"],
        "escalationCurve": build_escalation(35, "moderate"),
        "phases": [
            {"id": 1, "name": "Patient Intake", "icon": "🩺", "short": "Intake"},
            {"id": 2, "name": "Pre-Op", "icon": "📋", "short": "Pre-Op"},
            {"id": 3, "name": "Incision", "icon": "🔪", "short": "Incision"},
            {"id": 4, "name": "Nephrectomy", "icon": "⚕️", "short": "Procedure"},
            {"id": 5, "name": "Closing", "icon": "🪡", "short": "Closing"},
            {"id": 6, "name": "Post-Op", "icon": "📊", "short": "Post-Op"},
        ],
        "totalTicks": 35,
    },
    {
        "id": "hip-replacement",
        "name": "Total Hip Replacement",
        "category": "intermediate",
        "specialty": "Orthopedic",
        "description": "Total hip arthroplasty for osteoarthritis. Fat embolism and dislocation are key risks.",
        "patient": {
            "name": "Walter N.", "age": 68, "sex": "Male", "weight": "82 kg", "bloodType": "A+",
            "admission": "Right hip osteoarthritis with progressive pain and functional limitation",
            "mood": "Hopeful", "comorbidities": ["hypertension", "diabetes"],
            "baselineVitals": {"spo2": 97, "heart_rate": 82, "bp_systolic": 155, "bp_diastolic": 80, "temperature": 37.0, "respiratory_rate": 16},
        },
        "initialState": {"vitals_override": {"heart_rate": 82, "bp_systolic": 155}, "riskProfile": RISK_PROFILES["moderate"]},
        "complicationWeights": {"thrombosis": 4, "hemorrhage": 3, "hypoxia": 3, "nerve_injury": 2},
        "allowedComplications": ["thrombosis", "hemorrhage", "hypoxia", "nerve_injury"],
        "decisionArchetypes": ["POST_OP_MONITORING"],
        "escalationCurve": build_escalation(35, "moderate"),
        "phases": [
            {"id": 1, "name": "Patient Intake", "icon": "🩺", "short": "Intake"},
            {"id": 2, "name": "Pre-Op Planning", "icon": "📋", "short": "Pre-Op"},
            {"id": 3, "name": "Incision & Access", "icon": "🔪", "short": "Incision"},
            {"id": 4, "name": "Core Procedure", "icon": "⚕️", "short": "Procedure"},
            {"id": 5, "name": "Closing", "icon": "🪡", "short": "Closing"},
            {"id": 6, "name": "Post-Op", "icon": "📊", "short": "Post-Op"},
        ],
        "totalTicks": 35,
    },
    {
        "id": "breast-lumpectomy",
        "name": "Breast Lumpectomy",
        "category": "intermediate",
        "specialty": "Surgical Oncology",
        "description": "Breast-conserving surgery for early-stage breast carcinoma with sentinel node biopsy.",
        "patient": {
            "name": "Diana P.", "age": 52, "sex": "Female", "weight": "62 kg", "bloodType": "A+",
            "admission": "2cm right breast mass, biopsy-proven invasive ductal carcinoma",
            "mood": "Nervous but optimistic", "comorbidities": [],
            "baselineVitals": {"spo2": 98, "heart_rate": 76, "bp_systolic": 118, "bp_diastolic": 78, "temperature": 37.0, "respiratory_rate": 16},
        },
        "initialState": {"vitals_override": {}, "riskProfile": RISK_PROFILES["low"]},
        "complicationWeights": {"hemorrhage": 3, "infection": 3},
        "allowedComplications": ["hemorrhage", "infection"],
        "decisionArchetypes": ["INFECTION_MANAGEMENT"],
        "escalationCurve": build_escalation(25, "mild"),
        "phases": [
            {"id": 1, "name": "Patient Intake", "icon": "🩺", "short": "Intake"},
            {"id": 2, "name": "Pre-Op", "icon": "📋", "short": "Pre-Op"},
            {"id": 3, "name": "Incision", "icon": "🔪", "short": "Incision"},
            {"id": 4, "name": "Lumpectomy", "icon": "⚕️", "short": "Procedure"},
            {"id": 5, "name": "Closing", "icon": "🪡", "short": "Closing"},
            {"id": 6, "name": "Post-Op", "icon": "📊", "short": "Post-Op"},
        ],
        "totalTicks": 25,
    },
    {
        "id": "tympanoplasty",
        "name": "Tympanoplasty",
        "category": "intermediate",
        "specialty": "ENT",
        "description": "Tympanic membrane repair with graft placement. Hearing and facial nerve preservation critical.",
        "patient": {
            "name": "Ahmed S.", "age": 34, "sex": "Male", "weight": "72 kg", "bloodType": "B+",
            "admission": "Chronic left ear perforation with conductive hearing loss",
            "mood": "Hopeful", "comorbidities": [],
            "baselineVitals": {"spo2": 98, "heart_rate": 72, "bp_systolic": 120, "bp_diastolic": 80, "temperature": 37.0, "respiratory_rate": 16},
        },
        "initialState": {"vitals_override": {}, "riskProfile": RISK_PROFILES["low"]},
        "complicationWeights": {"infection": 4, "nerve_injury": 3},
        "allowedComplications": ["infection", "nerve_injury"],
        "decisionArchetypes": ["DIAGNOSTIC_STEP"],
        "escalationCurve": build_escalation(25, "mild"),
        "phases": [
            {"id": 1, "name": "Patient Intake", "icon": "🩺", "short": "Intake"},
            {"id": 2, "name": "Pre-Op", "icon": "📋", "short": "Pre-Op"},
            {"id": 3, "name": "Approach", "icon": "🔪", "short": "Approach"},
            {"id": 4, "name": "Grafting", "icon": "⚕️", "short": "Procedure"},
            {"id": 5, "name": "Closing", "icon": "🪡", "short": "Closing"},
            {"id": 6, "name": "Post-Op", "icon": "📊", "short": "Post-Op"},
        ],
        "totalTicks": 25,
    },
    {
        "id": "femoral-nail-fixation",
        "name": "Femoral Nail Fixation",
        "category": "intermediate",
        "specialty": "Orthopedic",
        "description": "Intramedullary nailing of femoral shaft fracture. Fat embolism and bleeding are key risks.",
        "patient": {
            "name": "Tom B.", "age": 35, "sex": "Male", "weight": "85 kg", "bloodType": "O+",
            "admission": "Right femoral shaft fracture from motorcycle accident",
            "mood": "In pain", "comorbidities": [],
            "baselineVitals": {"spo2": 95, "heart_rate": 110, "bp_systolic": 100, "bp_diastolic": 65, "temperature": 37.0, "respiratory_rate": 22},
        },
        "initialState": {"vitals_override": {"spo2": 95, "heart_rate": 110, "bp_systolic": 100, "respiratory_rate": 22}, "riskProfile": RISK_PROFILES["moderate"]},
        "complicationWeights": {"hemorrhage": 5, "hypoxia": 4},
        "allowedComplications": ["hemorrhage", "hypoxia"],
        "decisionArchetypes": ["HEMODYNAMIC_CONTROL"],
        "escalationCurve": build_escalation(30, "aggressive"),
        "phases": [
            {"id": 1, "name": "Resuscitation", "icon": "🩸", "short": "Resus"},
            {"id": 2, "name": "Pre-Op", "icon": "📋", "short": "Pre-Op"},
            {"id": 3, "name": "Reduction", "icon": "🔪", "short": "Reduction"},
            {"id": 4, "name": "Nailing", "icon": "⚙️", "short": "Nailing"},
            {"id": 5, "name": "Closing", "icon": "🪡", "short": "Closing"},
            {"id": 6, "name": "Post-Op", "icon": "📊", "short": "Post-Op"},
        ],
        "totalTicks": 30,
    },
    {
        "id": "rotator-cuff-repair",
        "name": "Rotator Cuff Repair",
        "category": "intermediate",
        "specialty": "Orthopedic",
        "description": "Arthroscopic rotator cuff repair with suture anchor fixation.",
        "patient": {
            "name": "Jennifer L.", "age": 55, "sex": "Female", "weight": "68 kg", "bloodType": "A+",
            "admission": "Right shoulder pain and weakness, MRI showing full-thickness supraspinatus tear",
            "mood": "Eager to recover", "comorbidities": [],
            "baselineVitals": {"spo2": 98, "heart_rate": 72, "bp_systolic": 120, "bp_diastolic": 80, "temperature": 37.0, "respiratory_rate": 16},
        },
        "initialState": {"vitals_override": {}, "riskProfile": RISK_PROFILES["low"]},
        "complicationWeights": {"nerve_injury": 3, "infection": 2},
        "allowedComplications": ["nerve_injury", "infection"],
        "decisionArchetypes": ["PAIN_MANAGEMENT"],
        "escalationCurve": build_escalation(25, "mild"),
        "phases": [
            {"id": 1, "name": "Patient Intake", "icon": "🩺", "short": "Intake"},
            {"id": 2, "name": "Pre-Op", "icon": "📋", "short": "Pre-Op"},
            {"id": 3, "name": "Arthroscopy", "icon": "🎥", "short": "Scope"},
            {"id": 4, "name": "Repair", "icon": "⚕️", "short": "Repair"},
            {"id": 5, "name": "Closing", "icon": "🪡", "short": "Closing"},
            {"id": 6, "name": "Post-Op", "icon": "📊", "short": "Post-Op"},
        ],
        "totalTicks": 25,
    },
    {
        "id": "rhinoplasty",
        "name": "Rhinoplasty",
        "category": "intermediate",
        "specialty": "ENT / Plastic Surgery",
        "description": "Open rhinoplasty for nasal deformity. Airway protection during post-op is critical.",
        "patient": {
            "name": "Sophia W.", "age": 27, "sex": "Female", "weight": "58 kg", "bloodType": "AB+",
            "admission": "Nasal deformity with breathing difficulty, requesting cosmetic and functional improvement",
            "mood": "Nervous", "comorbidities": [],
            "baselineVitals": {"spo2": 98, "heart_rate": 72, "bp_systolic": 115, "bp_diastolic": 75, "temperature": 37.0, "respiratory_rate": 16},
        },
        "initialState": {"vitals_override": {}, "riskProfile": RISK_PROFILES["low"]},
        "complicationWeights": {"hypoxia": 4, "hemorrhage": 3},
        "allowedComplications": ["hypoxia", "hemorrhage"],
        "decisionArchetypes": ["AIRWAY_STABILITY"],
        "escalationCurve": build_escalation(25, "mild"),
        "phases": [
            {"id": 1, "name": "Patient Intake", "icon": "🩺", "short": "Intake"},
            {"id": 2, "name": "Pre-Op", "icon": "📋", "short": "Pre-Op"},
            {"id": 3, "name": "Incision", "icon": "🔪", "short": "Incision"},
            {"id": 4, "name": "Reshaping", "icon": "⚕️", "short": "Procedure"},
            {"id": 5, "name": "Closing", "icon": "🪡", "short": "Closing"},
            {"id": 6, "name": "Post-Op", "icon": "📊", "short": "Post-Op"},
        ],
        "totalTicks": 25,
    },
    {
        "id": "parathyroidectomy",
        "name": "Parathyroidectomy",
        "category": "intermediate",
        "specialty": "ENT / Endocrine",
        "description": "Parathyroid adenoma removal. Calcium monitoring and RLN preservation are key.",
        "patient": {
            "name": "Helen T.", "age": 55, "sex": "Female", "weight": "70 kg", "bloodType": "A-",
            "admission": "Primary hyperparathyroidism, elevated calcium, parathyroid adenoma on sestamibi",
            "mood": "Concerned about calcium", "comorbidities": ["hypertension"],
            "baselineVitals": {"spo2": 98, "heart_rate": 78, "bp_systolic": 140, "bp_diastolic": 85, "temperature": 37.0, "respiratory_rate": 16},
        },
        "initialState": {"vitals_override": {"bp_systolic": 140}, "riskProfile": RISK_PROFILES["low"]},
        "complicationWeights": {"nerve_injury": 4, "hemorrhage": 2, "hypoxia": 2},
        "allowedComplications": ["nerve_injury", "hemorrhage", "hypoxia"],
        "decisionArchetypes": ["DIAGNOSTIC_STEP"],
        "escalationCurve": build_escalation(25, "mild"),
        "phases": [
            {"id": 1, "name": "Patient Intake", "icon": "🩺", "short": "Intake"},
            {"id": 2, "name": "Pre-Op", "icon": "📋", "short": "Pre-Op"},
            {"id": 3, "name": "Incision", "icon": "🔪", "short": "Incision"},
            {"id": 4, "name": "Adenoma Removal", "icon": "⚕️", "short": "Procedure"},
            {"id": 5, "name": "Closing", "icon": "🪡", "short": "Closing"},
            {"id": 6, "name": "Post-Op", "icon": "📊", "short": "Post-Op"},
        ],
        "totalTicks": 25,
    },

    # ── ADVANCED (12) ──
    {
        "id": "cabg",
        "name": "Heart Bypass (CABG)",
        "category": "advanced",
        "specialty": "Cardiovascular",
        "description": "Coronary artery bypass grafting with cardiopulmonary bypass. Ischemia and arrhythmia are critical.",
        "patient": {
            "name": "Robert M.", "age": 64, "sex": "Male", "weight": "88 kg", "bloodType": "A+",
            "admission": "Severe chest pain, multi-vessel coronary artery disease on angiography",
            "mood": "Lethargic", "comorbidities": ["hypertension", "diabetes"],
            "baselineVitals": {"spo2": 97, "heart_rate": 86, "bp_systolic": 163, "bp_diastolic": 80, "temperature": 37.0, "respiratory_rate": 16},
        },
        "initialState": {"vitals_override": {"heart_rate": 86, "bp_systolic": 163}, "riskProfile": RISK_PROFILES["high"]},
        "complicationWeights": {"cardiac_arrhythmia": 5, "hemorrhage": 4, "hypoxia": 3, "thrombosis": 2},
        "allowedComplications": ["cardiac_arrhythmia", "hemorrhage", "hypoxia", "thrombosis"],
        "decisionArchetypes": ["HEMODYNAMIC_CONTROL", "AIRWAY_STABILITY"],
        "escalationCurve": build_escalation(45, "aggressive"),
        "phases": [
            {"id": 1, "name": "Pre-Op Evaluation", "icon": "🩺", "short": "Pre-Op"},
            {"id": 2, "name": "Anesthesia & Induction", "icon": "💉", "short": "Induction"},
            {"id": 3, "name": "Sternotomy & Harvest", "icon": "🔪", "short": "Harvest"},
            {"id": 4, "name": "Cardiopulmonary Bypass", "icon": "🫀", "short": "CPB"},
            {"id": 5, "name": "Distal Anastomoses", "icon": "🪡", "short": "Distal"},
            {"id": 6, "name": "Proximal & Weaning", "icon": "📈", "short": "Proximal"},
            {"id": 7, "name": "Closure", "icon": "🪢", "short": "Close"},
            {"id": 8, "name": "ICU & Recovery", "icon": "🏥", "short": "ICU"},
        ],
        "totalTicks": 45,
    },
    {
        "id": "craniotomy",
        "name": "Craniotomy",
        "category": "advanced",
        "specialty": "Neurological",
        "description": "Frontal craniotomy for tumor resection. ICP management and neural preservation are paramount.",
        "patient": {
            "name": "Elena S.", "age": 41, "sex": "Female", "weight": "65 kg", "bloodType": "B+",
            "admission": "Severe headache, left-sided weakness, 4cm right frontal mass on MRI",
            "mood": "Confused", "comorbidities": [],
            "baselineVitals": {"spo2": 98, "heart_rate": 78, "bp_systolic": 125, "bp_diastolic": 80, "temperature": 37.0, "respiratory_rate": 16},
        },
        "initialState": {"vitals_override": {"bp_systolic": 125}, "riskProfile": RISK_PROFILES["high"]},
        "complicationWeights": {"hemorrhage": 5, "hypoxia": 3, "nerve_injury": 4, "cardiac_arrhythmia": 2},
        "allowedComplications": ["hemorrhage", "hypoxia", "nerve_injury", "cardiac_arrhythmia"],
        "decisionArchetypes": ["DIAGNOSTIC_STEP", "AIRWAY_STABILITY"],
        "escalationCurve": build_escalation(40, "aggressive"),
        "phases": [
            {"id": 1, "name": "Pre-Op Evaluation", "icon": "🩺", "short": "Pre-Op"},
            {"id": 2, "name": "Anesthesia & Positioning", "icon": "💉", "short": "Setup"},
            {"id": 3, "name": "Incision & Craniotomy", "icon": "🔪", "short": "Craniotomy"},
            {"id": 4, "name": "Dural Opening & Exposure", "icon": "🧠", "short": "Exposure"},
            {"id": 5, "name": "Tumor Resection", "icon": "⚕️", "short": "Resection"},
            {"id": 6, "name": "Closure", "icon": "🪡", "short": "Closure"},
            {"id": 7, "name": "Post-Op Care", "icon": "🏥", "short": "Recovery"},
        ],
        "totalTicks": 40,
    },
    {
        "id": "spinal-fusion",
        "name": "Spinal Fusion",
        "category": "advanced",
        "specialty": "Orthopedic / Neurosurgery",
        "description": "L4-L5 posterior spinal fusion with pedicle screws and interbody cage. Nerve monitoring critical.",
        "patient": {
            "name": "David R.", "age": 54, "sex": "Male", "weight": "95 kg", "bloodType": "O+",
            "admission": "Chronic lower back pain, disc herniation L4-L5, failed conservative treatment",
            "mood": "Hopeful but cautious", "comorbidities": ["hypertension"],
            "baselineVitals": {"spo2": 98, "heart_rate": 72, "bp_systolic": 100, "bp_diastolic": 68, "temperature": 37.0, "respiratory_rate": 16},
        },
        "initialState": {"vitals_override": {"bp_systolic": 100}, "riskProfile": RISK_PROFILES["high"]},
        "complicationWeights": {"nerve_injury": 5, "hemorrhage": 4, "infection": 3, "thrombosis": 2},
        "allowedComplications": ["nerve_injury", "hemorrhage", "infection", "thrombosis"],
        "decisionArchetypes": ["SURGICAL_DECISION"],
        "escalationCurve": build_escalation(40, "aggressive"),
        "phases": [
            {"id": 1, "name": "Consultation", "icon": "🧠", "short": "Neuro Exam"},
            {"id": 2, "name": "Positioning", "icon": "🛌", "short": "Prone"},
            {"id": 3, "name": "Exposure", "icon": "⚒️", "short": "Incision"},
            {"id": 4, "name": "Decompression", "icon": "🔬", "short": "Laminectomy"},
            {"id": 5, "name": "Fusion", "icon": "🔩", "short": "Screw/Cage"},
            {"id": 6, "name": "Verification", "icon": "📸", "short": "Final X-ray"},
        ],
        "totalTicks": 40,
    },
    {
        "id": "exploratory-laparotomy",
        "name": "Exploratory Laparotomy",
        "category": "advanced",
        "specialty": "Trauma Surgery",
        "description": "Emergent trauma laparotomy for penetrating injury. Damage control and hemorrhage control.",
        "patient": {
            "name": "Marcus Doe", "age": 28, "sex": "Male", "weight": "85 kg", "bloodType": "O-",
            "admission": "Gunshot wound to RUQ, resuscitated in the trauma bay — BP 92/60, HR 118",
            "mood": "Agitated/Obtunded", "comorbidities": [],
            "baselineVitals": {"spo2": 94, "heart_rate": 118, "bp_systolic": 92, "bp_diastolic": 60, "temperature": 36.5, "respiratory_rate": 24},
        },
        "initialState": {"vitals_override": {}, "riskProfile": RISK_PROFILES["critical"]},
        "complicationWeights": {"hemorrhage": 8, "cardiac_arrhythmia": 3, "infection": 3, "hypoxia": 2},
        "allowedComplications": ["hemorrhage", "cardiac_arrhythmia", "infection", "hypoxia"],
        "decisionArchetypes": ["HEMODYNAMIC_CONTROL", "INFECTION_MANAGEMENT"],
        "escalationCurve": build_escalation(35, "aggressive"),
        "phases": [
            {"id": 1, "name": "Resuscitation", "icon": "🩸", "short": "MTP/FAST"},
            {"id": 2, "name": "Control", "icon": "🔪", "short": "Laparotomy"},
            {"id": 3, "name": "Systematic Review", "icon": "🔍", "short": "Audit"},
            {"id": 4, "name": "Intervention", "icon": "✂️", "short": "Repair"},
            {"id": 5, "name": "Damage Control", "icon": "🩹", "short": "Packing"},
            {"id": 6, "name": "Stabilization", "icon": "🚑", "short": "ICU Handoff"},
        ],
        "totalTicks": 35,
    },
    {
        "id": "pulmonary-lobectomy",
        "name": "Pulmonary Lobectomy",
        "category": "advanced",
        "specialty": "Thoracic",
        "description": "Video-assisted thoracoscopic lobectomy for lung cancer. Air leak and respiratory failure are key risks.",
        "patient": {
            "name": "William C.", "age": 62, "sex": "Male", "weight": "80 kg", "bloodType": "B-",
            "admission": "2.5cm right upper lobe mass, biopsy-proven adenocarcinoma",
            "mood": "Resigned", "comorbidities": ["copd"],
            "baselineVitals": {"spo2": 94, "heart_rate": 82, "bp_systolic": 135, "bp_diastolic": 85, "temperature": 37.0, "respiratory_rate": 20},
        },
        "initialState": {"vitals_override": {"spo2": 94, "respiratory_rate": 20}, "riskProfile": RISK_PROFILES["high"]},
        "complicationWeights": {"hypoxia": 6, "hemorrhage": 3, "cardiac_arrhythmia": 3, "infection": 2},
        "allowedComplications": ["hypoxia", "hemorrhage", "cardiac_arrhythmia", "infection"],
        "decisionArchetypes": ["AIRWAY_STABILITY"],
        "escalationCurve": build_escalation(40, "aggressive"),
        "phases": [
            {"id": 1, "name": "Pre-Op", "icon": "🩺", "short": "Pre-Op"},
            {"id": 2, "name": "Positioning", "icon": "🛌", "short": "Lateral"},
            {"id": 3, "name": "VATS Access", "icon": "🔪", "short": "Access"},
            {"id": 4, "name": "Lobectomy", "icon": "⚕️", "short": "Resection"},
            {"id": 5, "name": "Closure", "icon": "🪡", "short": "Closing"},
            {"id": 6, "name": "Post-Op", "icon": "📊", "short": "Post-Op"},
        ],
        "totalTicks": 40,
    },
    {
        "id": "whipple",
        "name": "Whipple Procedure",
        "category": "advanced",
        "specialty": "Surgical Oncology",
        "description": "Pancreaticoduodenectomy for pancreatic head mass. Massive complication risk across all systems.",
        "patient": {
            "name": "Harold F.", "age": 67, "sex": "Male", "weight": "78 kg", "bloodType": "A+",
            "admission": "Pancreatic head mass with jaundice, weight loss, and elevated CA 19-9",
            "mood": "Somber", "comorbidities": ["diabetes", "hypertension"],
            "baselineVitals": {"spo2": 97, "heart_rate": 86, "bp_systolic": 155, "bp_diastolic": 85, "temperature": 37.2, "respiratory_rate": 16},
        },
        "initialState": {"vitals_override": {"heart_rate": 86, "bp_systolic": 155, "temperature": 37.2}, "riskProfile": RISK_PROFILES["critical"]},
        "complicationWeights": {"infection": 6, "hemorrhage": 5, "cardiac_arrhythmia": 3, "hypoxia": 3, "thrombosis": 2},
        "allowedComplications": ["infection", "hemorrhage", "cardiac_arrhythmia", "hypoxia", "thrombosis"],
        "decisionArchetypes": ["INFECTION_MANAGEMENT", "HEMODYNAMIC_CONTROL"],
        "escalationCurve": build_escalation(50, "aggressive"),
        "phases": [
            {"id": 1, "name": "Pre-Op", "icon": "🩺", "short": "Pre-Op"},
            {"id": 2, "name": "Exploration", "icon": "🔍", "short": "Explore"},
            {"id": 3, "name": "Resection", "icon": "🔪", "short": "Resect"},
            {"id": 4, "name": "Reconstruction", "icon": "🪡", "short": "Reconstruct"},
            {"id": 5, "name": "Closing", "icon": "🪢", "short": "Close"},
            {"id": 6, "name": "Post-Op", "icon": "🏥", "short": "ICU"},
        ],
        "totalTicks": 50,
    },
    {
        "id": "aaa-repair",
        "name": "AAA Repair",
        "category": "advanced",
        "specialty": "Vascular",
        "description": "Open abdominal aortic aneurysm repair. Rupture and massive hemorrhage are existential threats.",
        "patient": {
            "name": "George P.", "age": 72, "sex": "Male", "weight": "88 kg", "bloodType": "O+",
            "admission": "6.5cm infrarenal AAA with back pain, urgent repair indicated",
            "mood": "Worried", "comorbidities": ["hypertension", "diabetes", "copd"],
            "baselineVitals": {"spo2": 95, "heart_rate": 88, "bp_systolic": 170, "bp_diastolic": 95, "temperature": 37.0, "respiratory_rate": 18},
        },
        "initialState": {"vitals_override": {"spo2": 95, "heart_rate": 88, "bp_systolic": 170, "bp_diastolic": 95, "respiratory_rate": 18}, "riskProfile": RISK_PROFILES["critical"]},
        "complicationWeights": {"hemorrhage": 8, "cardiac_arrhythmia": 4, "hypoxia": 3, "thrombosis": 3},
        "allowedComplications": ["hemorrhage", "cardiac_arrhythmia", "hypoxia", "thrombosis"],
        "decisionArchetypes": ["HEMODYNAMIC_CONTROL"],
        "escalationCurve": build_escalation(45, "aggressive"),
        "phases": [
            {"id": 1, "name": "Pre-Op", "icon": "🩺", "short": "Pre-Op"},
            {"id": 2, "name": "Exposure", "icon": "🔪", "short": "Open"},
            {"id": 3, "name": "Clamping", "icon": "🩸", "short": "Clamp"},
            {"id": 4, "name": "Graft", "icon": "⚕️", "short": "Graft"},
            {"id": 5, "name": "Closing", "icon": "🪡", "short": "Close"},
            {"id": 6, "name": "Post-Op", "icon": "🏥", "short": "ICU"},
        ],
        "totalTicks": 45,
    },
    {
        "id": "radical-prostatectomy",
        "name": "Radical Prostatectomy",
        "category": "advanced",
        "specialty": "Urology",
        "description": "Radical retropubic prostatectomy for prostate cancer. Nerve-sparing and bleeding control critical.",
        "patient": {
            "name": "Frank D.", "age": 61, "sex": "Male", "weight": "86 kg", "bloodType": "A+",
            "admission": "Gleason 7 prostate adenocarcinoma, PSA 8.2, nerve-sparing candidate",
            "mood": "Anxious about function", "comorbidities": ["hypertension"],
            "baselineVitals": {"spo2": 98, "heart_rate": 76, "bp_systolic": 100, "bp_diastolic": 68, "temperature": 37.0, "respiratory_rate": 16},
        },
        "initialState": {"vitals_override": {"bp_systolic": 100}, "riskProfile": RISK_PROFILES["high"]},
        "complicationWeights": {"hemorrhage": 5, "nerve_injury": 4, "infection": 2},
        "allowedComplications": ["hemorrhage", "nerve_injury", "infection"],
        "decisionArchetypes": ["SURGICAL_DECISION"],
        "escalationCurve": build_escalation(35, "moderate"),
        "phases": [
            {"id": 1, "name": "Pre-Op", "icon": "🩺", "short": "Pre-Op"},
            {"id": 2, "name": "Exposure", "icon": "🔪", "short": "Open"},
            {"id": 3, "name": "Dissection", "icon": "🔍", "short": "Dissect"},
            {"id": 4, "name": "Prostatectomy", "icon": "⚕️", "short": "Procedure"},
            {"id": 5, "name": "Anastomosis", "icon": "🪡", "short": "Anastomosis"},
            {"id": 6, "name": "Post-Op", "icon": "📊", "short": "Post-Op"},
        ],
        "totalTicks": 35,
    },
    {
        "id": "esophagectomy",
        "name": "Esophagectomy",
        "category": "advanced",
        "specialty": "Thoracic / Surgical Oncology",
        "description": "Ivor Lewis esophagectomy for esophageal cancer. Anastomotic leak and respiratory failure are key risks.",
        "patient": {
            "name": "Richard B.", "age": 63, "sex": "Male", "weight": "72 kg", "bloodType": "O-",
            "admission": "Distal esophageal adenocarcinoma, dysphagia, 15lb weight loss",
            "mood": "Determined", "comorbidities": ["copd"],
            "baselineVitals": {"spo2": 95, "heart_rate": 80, "bp_systolic": 128, "bp_diastolic": 78, "temperature": 37.0, "respiratory_rate": 18},
        },
        "initialState": {"vitals_override": {"spo2": 95, "respiratory_rate": 18}, "riskProfile": RISK_PROFILES["high"]},
        "complicationWeights": {"hypoxia": 5, "infection": 5, "hemorrhage": 3, "cardiac_arrhythmia": 2},
        "allowedComplications": ["hypoxia", "infection", "hemorrhage", "cardiac_arrhythmia"],
        "decisionArchetypes": ["AIRWAY_STABILITY", "INFECTION_MANAGEMENT"],
        "escalationCurve": build_escalation(45, "aggressive"),
        "phases": [
            {"id": 1, "name": "Pre-Op", "icon": "🩺", "short": "Pre-Op"},
            {"id": 2, "name": "Abdominal Phase", "icon": "🔪", "short": "Abdominal"},
            {"id": 3, "name": "Thoracic Phase", "icon": "🫁", "short": "Thoracic"},
            {"id": 4, "name": "Anastomosis", "icon": "🪡", "short": "Anastomosis"},
            {"id": 5, "name": "Closing", "icon": "🪢", "short": "Close"},
            {"id": 6, "name": "Post-Op", "icon": "🏥", "short": "ICU"},
        ],
        "totalTicks": 45,
    },
    {
        "id": "hepatic-lobectomy",
        "name": "Hepatic Lobectomy",
        "category": "advanced",
        "specialty": "Hepatobiliary",
        "description": "Right hepatic lobectomy for colorectal liver metastasis. Bleeding control is the primary challenge.",
        "patient": {
            "name": "Nancy W.", "age": 59, "sex": "Female", "weight": "68 kg", "bloodType": "B+",
            "admission": "Solitary right lobe liver metastasis from treated colon cancer",
            "mood": "Cautiously optimistic", "comorbidities": [],
            "baselineVitals": {"spo2": 98, "heart_rate": 78, "bp_systolic": 122, "bp_diastolic": 78, "temperature": 37.0, "respiratory_rate": 16},
        },
        "initialState": {"vitals_override": {}, "riskProfile": RISK_PROFILES["high"]},
        "complicationWeights": {"hemorrhage": 7, "cardiac_arrhythmia": 3, "infection": 2, "hypoxia": 2},
        "allowedComplications": ["hemorrhage", "cardiac_arrhythmia", "infection", "hypoxia"],
        "decisionArchetypes": ["HEMODYNAMIC_CONTROL"],
        "escalationCurve": build_escalation(40, "aggressive"),
        "phases": [
            {"id": 1, "name": "Pre-Op", "icon": "🩺", "short": "Pre-Op"},
            {"id": 2, "name": "Exposure", "icon": "🔪", "short": "Open"},
            {"id": 3, "name": "Mobilization", "icon": "🔍", "short": "Mobilize"},
            {"id": 4, "name": "Resection", "icon": "⚕️", "short": "Resect"},
            {"id": 5, "name": "Hemostasis", "icon": "🩸", "short": "Hemostasis"},
            {"id": 6, "name": "Post-Op", "icon": "📊", "short": "Post-Op"},
        ],
        "totalTicks": 40,
    },
    {
        "id": "lumbar-microdiscectomy",
        "name": "Lumbar Microdiscectomy",
        "category": "advanced",
        "specialty": "Neurosurgery",
        "description": "Microsurgical discectomy for lumbar disc herniation. Nerve root protection and dural preservation.",
        "patient": {
            "name": "Karen S.", "age": 42, "sex": "Female", "weight": "70 kg", "bloodType": "A+",
            "admission": "L5-S1 disc herniation with progressive radiculopathy, failed 6 weeks of conservative care",
            "mood": "In pain", "comorbidities": [],
            "baselineVitals": {"spo2": 98, "heart_rate": 78, "bp_systolic": 93, "bp_diastolic": 63, "temperature": 37.0, "respiratory_rate": 16},
        },
        "initialState": {"vitals_override": {}, "riskProfile": RISK_PROFILES["moderate"]},
        "complicationWeights": {"nerve_injury": 5, "hemorrhage": 2, "infection": 2},
        "allowedComplications": ["nerve_injury", "hemorrhage", "infection"],
        "decisionArchetypes": ["PAIN_MANAGEMENT"],
        "escalationCurve": build_escalation(30, "moderate"),
        "phases": [
            {"id": 1, "name": "Pre-Op", "icon": "🩺", "short": "Pre-Op"},
            {"id": 2, "name": "Positioning", "icon": "🛌", "short": "Prone"},
            {"id": 3, "name": "Exposure", "icon": "🔪", "short": "Open"},
            {"id": 4, "name": "Discectomy", "icon": "⚕️", "short": "Procedure"},
            {"id": 5, "name": "Closing", "icon": "🪡", "short": "Close"},
            {"id": 6, "name": "Post-Op", "icon": "📊", "short": "Post-Op"},
        ],
        "totalTicks": 30,
    },
    {
        "id": "cabg-offpump",
        "name": "Off-Pump CABG",
        "category": "advanced",
        "specialty": "Cardiovascular",
        "description": "Beating-heart coronary artery bypass. Stabilize myocardium, perform anastomoses without cardiopulmonary bypass.",
        "patient": {
            "name": "James T.", "age": 68, "sex": "Male", "weight": "82 kg", "bloodType": "O-",
            "admission": "Triple-vessel coronary disease, poor candidate for CPB due to severe COPD",
            "mood": "Anxious", "comorbidities": ["COPD", "hypertension", "diabetes"],
            "baselineVitals": {"spo2": 94, "heart_rate": 90, "bp_systolic": 155, "bp_diastolic": 85, "temperature": 37.0, "respiratory_rate": 20},
        },
        "initialState": {"vitals_override": {"spo2": 94, "heart_rate": 90, "bp_systolic": 155}, "riskProfile": RISK_PROFILES["high"]},
        "complicationWeights": {"cardiac_arrhythmia": 6, "hemorrhage": 4, "hypoxia": 5, "thrombosis": 3},
        "allowedComplications": ["cardiac_arrhythmia", "hemorrhage", "hypoxia", "thrombosis"],
        "decisionArchetypes": ["HEMODYNAMIC_CONTROL", "AIRWAY_STABILITY"],
        "escalationCurve": build_escalation(45, "aggressive"),
        "phases": [
            {"id": 1, "name": "Pre-Op Evaluation", "icon": "🩺", "short": "Pre-Op"},
            {"id": 2, "name": "Anesthesia & Induction", "icon": "💉", "short": "Induction"},
            {"id": 3, "name": "Sternotomy & Harvest", "icon": "🔪", "short": "Harvest"},
            {"id": 4, "name": "Stabilization & Exposure", "icon": "🫀", "short": "Stabilize"},
            {"id": 5, "name": "Distal Anastomoses", "icon": "🪡", "short": "Distal"},
            {"id": 6, "name": "Proximal Anastomoses", "icon": "📈", "short": "Proximal"},
            {"id": 7, "name": "Closure", "icon": "🪢", "short": "Close"},
            {"id": 8, "name": "ICU & Recovery", "icon": "🏥", "short": "ICU"},
        ],
        "totalTicks": 45,
    },
]

# ════════════════════════════════════════════════════
#  REGISTRY LOOKUPS
# ════════════════════════════════════════════════════

PROCEDURE_REGISTRY: Dict[str, Dict[str, Any]] = {p["id"]: p for p in ALL_PROCEDURES}


def get_procedure(proc_id: str) -> Optional[Dict[str, Any]]:
    # Return None for unknown ids so callers can 404/validate instead of
    # silently booting the wrong surgery (previously fell back to appendectomy).
    entry = PROCEDURE_REGISTRY.get(proc_id)
    if entry is None:
        return None
    # Deep copy: engines mutate the risk profile in place (e.g. scaling
    # deterioration_rate by ASA class). Returning the shared registry dict would
    # let that mutation compound across every session ever created, which after
    # enough runs explodes deterioration_rate astronomically and instantly kills
    # every patient. Callers get an isolated snapshot they own.
    return copy.deepcopy(entry)


def list_procedures() -> List[Dict[str, Any]]:
    return ALL_PROCEDURES


def procedure_exists(proc_id: str) -> bool:
    return proc_id in PROCEDURE_REGISTRY
