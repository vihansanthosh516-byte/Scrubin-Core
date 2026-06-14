"""Physiology ↔ Cognition Bridge – Phase 5.2.5.

Provides a deterministic, read‑only snapshot of the physiological state that
cognition layers consume. The snapshot is immutable, hash‑stable, and contains
only deterministic transforms (no random numbers, no timestamps).
"""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from typing import Dict, Any

from scrubin.physiology.hidden_state import project_observable

# ---------------------------------------------------------------------------
# Snapshot definition – immutable, deterministic
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CognitionPhysiologySnapshot:
    """Immutable snapshot fed to the cognition stack.

    Attributes
    ----------
    tick: int
        Current simulation tick.
    vitals: Dict[str, float]
        Core vital signs (HR, BP, RR, Temp, SpO2).
    labs: Dict[str, float]
        Laboratory values derived deterministically from hidden state.
    symptoms: Dict[str, bool]
        Binary clinical signs derived deterministically.
    derived_features: Dict[str, float]
        Additional deterministic features (e.g., respiratory efficiency).
    risk_signals: Dict[str, float]
        Deterministic risk indices (shock, respiratory failure, renal failure,
        sepsis probability).
    hidden_state_projection: Dict[str, Any]
        Direct deterministic view of the hidden state (for advanced cognition).
    """

    tick: int
    vitals: Dict[str, float]
    labs: Dict[str, float]
    symptoms: Dict[str, bool]
    derived_features: Dict[str, float]
    risk_signals: Dict[str, float]
    hidden_state_projection: Dict[str, Any]

    def to_dict(self) -> dict:
        return {
            "tick": self.tick,
            "vitals": self.vitals,
            "labs": self.labs,
            "symptoms": self.symptoms,
            "derived_features": self.derived_features,
            "risk_signals": self.risk_signals,
            "hidden_state_projection": self.hidden_state_projection,
        }

    @staticmethod
    def from_world(world) -> "CognitionPhysiologySnapshot":
        """Factory – deterministic projection from a ``SimulationWorld``.

        The function is pure (no side‑effects) and always returns the same
        snapshot for an identical world state.  All dictionary construction uses
        sorted keys to guarantee a stable JSON representation.
        """
        # 1️⃣  Observable projection (vitals, labs, symptoms) via the existing helper
        obs = project_observable(world.hidden_state)

        # 2️⃣  Split into required layers
        vitals = {
            "heart_rate": obs.get("heart_rate"),
            "blood_pressure": obs.get("blood_pressure"),
            "respiratory_rate": obs.get("respiratory_rate"),
            "temperature": obs.get("temperature"),
            "SpO2": obs.get("SpO2"),
        }
        labs = {k: v for k, v in sorted(obs.get("labs", {}).items())}
        symptoms = {k: v for k, v in sorted(obs.get("clinical_signs", {}).items())}

        # 3️⃣  Deterministic derived features – simple example
        derived_features = {
            "respiratory_efficiency": round(vitals["SpO2"] / 100.0, 3) if vitals.get("SpO2") is not None else 0.0,
        }

        # 4️⃣  Deterministic risk signals – rule‑based (no randomness)
        risk_signals = {
            "shock_risk": 1.0 if vitals.get("blood_pressure", 0) < 90 else 0.0,
            "respiratory_failure_risk": 1.0 if vitals.get("respiratory_rate", 0) > 25 else 0.0,
            "renal_failure_risk": 1.0 if getattr(world.organ_state, "renal", None) and getattr(world.organ_state.renal, "health", 1.0) < 0.3 else 0.0,
            # sepsis index derived from hidden state – deterministic scalar
            "sepsis_probability_index": float(world.hidden_state.get("inflammation_index", 0.0)),
        }

        # 5️⃣  Hidden‑state projection (sorted for deterministic JSON)
        hidden_state_projection = {k: v for k, v in sorted(world.hidden_state.items())}

        # 6️⃣  Assemble snapshot
        return CognitionPhysiologySnapshot(
            tick=world.tick,
            vitals=vitals,
            labs=labs,
            symptoms=symptoms,
            derived_features=derived_features,
            risk_signals=risk_signals,
            hidden_state_projection=hidden_state_projection,
        )


def build_cognition_snapshot(world) -> CognitionPhysiologySnapshot:
    """Public helper – returns a deterministic snapshot for the given world.

    The function is a thin wrapper around ``CognitionPhysiologySnapshot.from_world``
    and exists for backward compatibility with existing code that expects a
    ``build_cognition_snapshot`` name.
    """
    return CognitionPhysiologySnapshot.from_world(world)
