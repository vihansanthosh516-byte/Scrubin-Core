"""Deterministic physiology engine for ProcedureScenario execution.

The engine evolves a frozen ``PhysiologyState`` each simulation tick based on:
* baseline physiology (from the scenario)
* active complications (from ``ComplicationEngine``)
* optional per‑step modifiers defined in the scenario
All updates are performed with ``dataclasses.replace`` to preserve immutability.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from typing import Dict, Tuple, List

# ---------------------------------------------------------------------------
# Immutable physiology state
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class PhysiologyState:
    HR: float = 80.0
    SBP: float = 120.0
    DBP: float = 80.0
    MAP: float = 93.3
    SpO2: float = 98.0
    RR: float = 12.0
    EtCO2: float = 35.0
    Temp: float = 37.0
    BloodVolume: float = 5000.0  # mL
    OxygenDebt: float = 0.0
    Lactate: float = 1.0
    CardiacOutput: float = 5.0
    OrganPerfusionScore: float = 100.0
    deterministic_id: str = ""

    def __post_init__(self) -> None:
        # Compute a deterministic identifier for the state (used for replay).
        # Concatenate all fields in a fixed order.
        fields = (
            self.HR,
            self.SBP,
            self.DBP,
            self.MAP,
            self.SpO2,
            self.RR,
            self.EtCO2,
            self.Temp,
            self.BloodVolume,
            self.OxygenDebt,
            self.Lactate,
            self.CardiacOutput,
            self.OrganPerfusionScore,
        )
        concatenated = "|".join(str(f) for f in fields)
        object.__setattr__(self, "deterministic_id", hashlib.sha256(concatenated.encode()).hexdigest())

# ---------------------------------------------------------------------------
# Engine implementation
# ---------------------------------------------------------------------------

class PhysiologyEngine:
    """Deterministic per‑tick physiology updater.

    The engine uses scenario‑defined baseline values and optional per‑step
    modifiers.  Complication impacts are looked up from ``scenario.
    complication_parameters``; if a parameter is missing a small default impact
    is applied.
    """

    # Default impacts for known complication IDs (used when scenario does not
    # provide explicit parameters).
    DEFAULT_COMPLICATION_IMPACTS: Dict[str, Dict[str, float]] = {
        "hemorrhage": {"BloodVolume": -200.0, "SBP": -5.0, "HR": 2.0},
        "hypoxia": {"SpO2": -3.0, "HR": 1.0},
        "arrhythmia": {"HR": 5.0},
        "sepsis": {"Temp": 0.5, "HR": 3.0, "Lactate": 0.2},
        "acidosis": {"Lactate": 0.5},
        "hypercarbia": {"EtCO2": 5.0},
        "hypothermia": {"Temp": -0.5},
        "pneumothorax": {"SpO2": -2.0, "RR": -1.0},
        "arterial_bleeding": {"BloodVolume": -250.0, "SBP": -10.0, "HR": 3.0},
        "venous_bleeding": {"BloodVolume": -150.0, "SBP": -5.0, "HR": 2.0},
        "bile_leak": {"Temp": 0.3, "HR": 2.0},
        "bowel_perforation": {"Temp": 0.5, "HR": 3.0},
        "ureter_injury": {"HR": 1.0},
        "co2_embolism": {"SpO2": -4.0, "HR": 5.0},
        "equipment_failure": {},
        "instrument_contamination": {"Temp": 0.2, "HR": 1.0},
        "anesthetic_instability": {"SBP": -5.0, "HR": 5.0},
    }

    def __init__(self, baseline: Dict[str, float] | None = None):
        self.baseline = baseline or {}

    def initial_state(self) -> PhysiologyState:
        """Create the initial immutable physiology state.

        Missing fields fall back to the defaults defined in ``PhysiologyState``.
        """
        init_kwargs = {
            "HR": self.baseline.get("HR", 80.0),
            "SBP": self.baseline.get("SBP", 120.0),
            "DBP": self.baseline.get("DBP", 80.0),
            "SpO2": self.baseline.get("SpO2", 98.0),
            "RR": self.baseline.get("RR", 12.0),
            "EtCO2": self.baseline.get("EtCO2", 35.0),
            "Temp": self.baseline.get("Temp", 37.0),
            "BloodVolume": self.baseline.get("BloodVolume", 5000.0),
            "OxygenDebt": self.baseline.get("OxygenDebt", 0.0),
            "Lactate": self.baseline.get("Lactate", 1.0),
            "CardiacOutput": self.baseline.get("CardiacOutput", 5.0),
            "OrganPerfusionScore": self.baseline.get("OrganPerfusionScore", 100.0),
        }
        # MAP is derived; we compute after creating the state.
        state = PhysiologyState(**init_kwargs)
        # Compute MAP deterministically from SBP and DBP.
        map_val = (state.SBP + 2 * state.DBP) / 3.0
        state = replace(state, MAP=map_val)
        return state

    def update(
        self,
        state: PhysiologyState,
        active_complications: Tuple[str, ...],
        step_modifiers: Dict[str, float] | None = None,
    ) -> Tuple[PhysiologyState, List[Dict]]:
        """Perform a deterministic tick update.

        * ``active_complications`` – tuple of currently active complication IDs.
        * ``step_modifiers`` – optional per‑step physiology delta mapping (e.g.,
          from a completed step).  Keys correspond to ``PhysiologyState`` fields.
        Returns the new state and a list of deterministic events.
        """
        events: List[Dict] = []
        new_state = state
        # Apply complication impacts.
        for cid in active_complications:
            impacts = self.DEFAULT_COMPLICATION_IMPACTS.get(cid, {})
            for field, delta in impacts.items():
                current = getattr(new_state, field)
                new_state = replace(new_state, **{field: current + delta})
            events.append({"type": "ComplicationProgressed", "complication": cid})
        # Apply step modifiers if provided.
        if step_modifiers:
            for field, delta in step_modifiers.items():
                if hasattr(new_state, field):
                    current = getattr(new_state, field)
                    new_state = replace(new_state, **{field: current + delta})
        # Derived metrics – deterministic formulas.
        map_val = (new_state.SBP + 2 * new_state.DBP) / 3.0
        new_state = replace(new_state, MAP=map_val)
        # Simple cardiac output proxy – proportional to MAP.
        co = max(0.0, map_val * 0.04)  # arbitrary deterministic scaling
        new_state = replace(new_state, CardiacOutput=co)
        # Organ perfusion – depends on cardiac output and blood volume.
        perf = max(0.0, (co / max(1.0, new_state.BloodVolume / 1000.0)) * 10.0)
        new_state = replace(new_state, OrganPerfusionScore=perf)
        events.append({"type": "PhysiologyUpdated", "state": new_state})
        return new_state, events
