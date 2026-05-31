"""Stub TissueConsequenceEngine for deterministic testing.

The full implementation is not required for the Phase O.7.1 intent
synthesis tests. This stub provides a minimal ``evolve`` method that returns
the world unchanged, preserving deterministic replay behavior.
"""

from __future__ import annotations

class TissueConsequenceEngine:
    """Placeholder engine – no‑op implementation."""
    def __init__(self, rng):
        self.rng = rng

    def evolve(self, world):
        """Return the world unchanged (deterministic no‑op)."""
        return world
