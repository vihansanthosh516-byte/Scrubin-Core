"""Stub CompetencyEvolutionEngine for deterministic testing.

The original implementation contained syntax and import errors and is not needed
for the deterministic intent synthesis tests. This placeholder provides a
minimal API matching the expected ``evolve`` method.
"""

from __future__ import annotations

class CompetencyEvolutionEngine:
    """Deterministic no‑op competency evolution engine."""
    def __init__(self, rng):
        self.rng = rng

    def evolve(self, world):
        """Return the world unchanged (deterministic)."""
        return world
