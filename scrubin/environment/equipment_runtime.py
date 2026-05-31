"""Stub EquipmentRuntimeEngine for deterministic testing.

The full implementation would manage equipment state, failures, and interaction
with procedures. For the current deterministic intent synthesis tests a
no‑op placeholder suffices.
"""

from __future__ import annotations

class EquipmentRuntimeEngine:
    """Placeholder – deterministic no‑op implementation."""
    def __init__(self, rng):
        self.rng = rng

    def evolve(self, world):
        """Return the world unchanged (deterministic)."""
        return world
