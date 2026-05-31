"""Stub ContaminationEcologyEngine for deterministic testing.

The full contamination ecology engine is not required for the intent
synthesis tests. This placeholder provides a minimal API that matches the
expected usage in ``physiologic_evolution``.
"""

from __future__ import annotations

class ContaminationEcologyEngine:
    """Placeholder – no‑op implementation of the contamination ecology engine."""
    def __init__(self, rng):
        self.rng = rng

    def evolve(self, world):
        """Return the world unchanged (deterministic no‑op)."""
        return world
