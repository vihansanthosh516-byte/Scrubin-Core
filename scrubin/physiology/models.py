"""Physiology model definitions for deterministic simulation.

This module defines immutable dataclasses that represent the patient physiological
state and provide deterministic identifiers for replay certification.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, replace
from typing import Dict, Tuple

# ---------------------------------------------------------------------------
# Core physiology state – a flat collection of key vitals and derived metrics.
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class PhysiologyState:
    """Immutable snapshot of patient physiology.

    The fields cover basic vitals and derived metrics needed for deterministic
    simulation.  All updates must be performed via ``replace`` to preserve
    immutability.
    """
    HR: float = 80.0
    SBP: float = 120.0
    DBP: float = 80.0
    MAP: float = 93.33333333333333
    SpO2: float = 98.0
    RR: float = 12.0
    EtCO2: float = 35.0
    Temp: float = 37.0
    BloodVolume: float = 5000.0  # mL
    OxygenDebt: float = 0.0
    Lactate: float = 1.0
    CardiacOutput: float = 5.0
    OrganPerfusionScore: float = 100.0
    deterministic_id: str = field(init=False)

    def __post_init__(self) -> None:
        # Deterministic identifier – hash of ordered field values.
        parts = [
            f"{self.HR:.5f}",
            f"{self.SBP:.5f}",
            f"{self.DBP:.5f}",
            f"{self.MAP:.5f}",
            f"{self.SpO2:.5f}",
            f"{self.RR:.5f}",
            f"{self.EtCO2:.5f}",
            f"{self.Temp:.5f}",
            f"{self.BloodVolume:.5f}",
            f"{self.OxygenDebt:.5f}",
            f"{self.Lactate:.5f}",
            f"{self.CardiacOutput:.5f}",
            f"{self.OrganPerfusionScore:.5f}",
        ]
        combined = "|".join(parts)
        object.__setattr__(self, "deterministic_id", hashlib.sha256(combined.encode()).hexdigest())

    # -------------------------------------------------------------------
    # Helper to apply arbitrary delta mapping via replace.
    # -------------------------------------------------------------------
    def with_updates(self, updates: Dict[str, float]) -> "PhysiologyState":
        new_state = self
        for key, val in updates.items():
            if hasattr(self, key):
                new_state = replace(new_state, **{key: val})
        return new_state
