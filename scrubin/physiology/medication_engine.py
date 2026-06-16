"""Deterministic medication engine.

The engine tracks active medication doses and applies their deterministic effects to a
``PhysiologyState`` each tick.  All state updates are performed via immutable
``replace`` calls; no randomness or timestamps are used.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Dict, List, Tuple

from .models import PhysiologyState

# Simple deterministic effect mapping for a few representative drugs.
# Each entry maps a medication name to a dict of physiology field deltas that are
# applied while the medication is active.
MED_EFFECTS: Dict[str, Dict[str, float]] = {
    "vasopressor": {"SBP": 10.0, "HR": -2.0},
    "fluid": {"BloodVolume": 200.0},
    "blood": {"BloodVolume": 500.0},
    "sedative": {"HR": -5.0, "SpO2": -1.0},
    "analgesic": {},  # No direct phys effect in this simplified model.
}

# Decay factor per tick for drug amount – deterministic.
DECAY_FACTOR = 0.1  # 10% of remaining amount decays each tick.


@dataclass(frozen=True, slots=True)
class MedicationState:
    """Immutable representation of a single medication.

    ``name`` – identifier matching a key in ``MED_EFFECTS``.
    ``amount`` – remaining dose (arbitrary units).
    """
    name: str
    amount: float
    deterministic_id: str = field(init=False)

    def __post_init__(self) -> None:
        import hashlib

        combined = f"{self.name}:{self.amount:.6f}"
        object.__setattr__(self, "deterministic_id", hashlib.sha256(combined.encode()).hexdigest())

    def with_amount(self, amount: float) -> "MedicationState":
        return replace(self, amount=amount)


class MedicationEngine:
    """Engine that manages deterministic medication administration.

    ``active_meds`` – tuple of ``MedicationState`` objects representing currently
    administered drugs.
    """

    def __init__(self, active_meds: Tuple[MedicationState, ...] = ()):  # noqa: B008 (default mutable ignored because tuple is immutable)
        self.active_meds = active_meds

    # ---------------------------------------------------------------------
    # Administration – returns a new engine with the drug added.
    # ---------------------------------------------------------------------
    def administer(self, name: str, amount: float) -> "MedicationEngine":
        new_med = MedicationState(name=name, amount=amount)
        return MedicationEngine(self.active_meds + (new_med,))

    # ---------------------------------------------------------------------
    # Tick processing – applies drug effects and decays amounts.
    # ---------------------------------------------------------------------
    def tick(self, phys_state: PhysiologyState) -> Tuple[PhysiologyState, List[Dict], "MedicationEngine"]:
        """Apply active medication effects to ``phys_state``.

        Returns a tuple ``(new_phys_state, events, new_engine)`` where ``new_engine``
        has updated medication amounts after deterministic decay.
        """
        events: List[Dict] = []
        cumulative_effects: Dict[str, float] = {}
        updated_meds: List[MedicationState] = []
        for med in self.active_meds:
            # Apply effect if defined.
            effects = MED_EFFECTS.get(med.name, {})
            for field, delta in effects.items():
                cumulative_effects[field] = cumulative_effects.get(field, 0.0) + delta
            # Decay amount.
            new_amount = max(0.0, med.amount * (1.0 - DECAY_FACTOR))
            if new_amount > 0.0:
                updated_meds.append(med.with_amount(new_amount))
            # Record administration event.
            events.append({"type": "MedicationEffect", "medication": med.name, "applied_delta": effects})
        # Apply cumulative effects to physiology.
        new_phys = phys_state
        for field, delta in cumulative_effects.items():
            if hasattr(new_phys, field):
                cur = getattr(new_phys, field)
                new_phys = replace(new_phys, **{field: cur + delta})
        # Return new medication engine with updated meds.
        new_engine = MedicationEngine(tuple(updated_meds))
        return new_phys, events, new_engine
