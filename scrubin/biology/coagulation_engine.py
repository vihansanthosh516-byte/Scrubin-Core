"""Coagulation & hemostasis engine placeholder.

The real engine would model clot formation, platelet consumption, fibrinolysis,
coagulopathy, thrombosis risk, and hemorrhage instability.  This stub provides a
minimal deterministic interface compatible with the rest of the system.
"""

from __future__ import annotations

from scrubin.biology.state import SystemsBiologyState


class CoagulationEngine:
    def __init__(self, rng):
        self.rng = rng

    def evolve(self, bio: SystemsBiologyState) -> SystemsBiologyState:
        # No‑op placeholder – real logic lives in SystemsBiologyEngine.
        return bio
