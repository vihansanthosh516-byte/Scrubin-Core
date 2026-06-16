"""Deterministic physiology engine.

The engine evolves a ``PhysiologyState`` each simulation tick based on:
* baseline values supplied at construction
* per‑tick deterministic deltas (e.g., blood loss, medication effects)
* derived metric recomputation (MAP, CardiacOutput, OrganPerfusionScore)

All state transitions are immutable – a new ``PhysiologyState`` instance is
returned together with a list of deterministic event dictionaries.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from dataclasses import replace

from .models import PhysiologyState


class PhysiologyEngine:
    """Deterministic engine for evolving patient physiology.

    ``baseline`` – optional mapping of initial vitals.  Missing fields fall back to
    defaults defined in :class:`PhysiologyState`.
    """

    def __init__(self, baseline: Dict[str, float] | None = None):
        self.baseline = baseline or {}

    def initial_state(self) -> PhysiologyState:
        """Create the initial immutable physiology snapshot.

        Baseline values override defaults where supplied.
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
        }
        state = PhysiologyState(**init_kwargs)
        # Re‑compute derived MAP and dependent metrics.
        map_val = (state.SBP + 2 * state.DBP) / 3.0
        co = max(0.0, map_val * 0.04)
        perf = max(0.0, (co / max(1.0, state.BloodVolume / 1000.0)) * 10.0)
        state = replace(state, MAP=map_val, CardiacOutput=co, OrganPerfusionScore=perf)
        return state

    def update(
        self,
        state: PhysiologyState,
        deltas: Dict[str, float] | None = None,
    ) -> Tuple[PhysiologyState, List[Dict]]:
        """Perform a deterministic tick update.

        ``deltas`` – mapping of field names to new values.  Only fields present in
        :class:`PhysiologyState` are updated; unknown keys are ignored.
        Returns the new state and a list of deterministic events describing the
        change.
        """
        deltas = deltas or {}
        # Apply explicit deltas.
        new_state = state
        for key, val in deltas.items():
            if hasattr(state, key):
                new_state = replace(new_state, **{key: val})
        # Re‑compute derived metrics deterministically.
        map_val = (new_state.SBP + 2 * new_state.DBP) / 3.0
        co = max(0.0, map_val * 0.04)
        perf = max(0.0, (co / max(1.0, new_state.BloodVolume / 1000.0)) * 10.0)
        new_state = replace(new_state, MAP=map_val, CardiacOutput=co, OrganPerfusionScore=perf)
        # Simple event payload – full state snapshot for deterministic replay.
        events: List[Dict] = [{"type": "PhysiologyUpdated", "state": new_state}]
        return new_state, events
