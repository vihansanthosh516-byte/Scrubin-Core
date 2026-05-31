"""Stub FrictionEngine for deterministic testing.

Provides a minimal deterministic implementation required for the
PhysiologicEvolutionEngine import. The real engine would model
operational friction (delays, failures) but for tests it can be a no‑op.
"""

from __future__ import annotations

class FrictionEngine:
    """Placeholder – deterministic no‑op friction engine."""
    def __init__(self, rng):
        self.rng = rng

    def evolve(self, world):
        """Return the world unchanged (deterministic)."""
        return world
