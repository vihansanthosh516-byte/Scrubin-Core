"""Deterministic stress injection engine.

Creates a deterministic set of ``StressVector`` objects based solely on the
provided ``ScenarioSeed``.  The mapping is rule‑based and does not use any random
or external data.
"""

from __future__ import annotations

from .models import ScenarioSeed, StressVector


class StressInjectionEngine:
    """Generate deterministic stress vectors from a seed.

    The implementation maps the seed hash to a fixed list of stress vectors.
    The mapping is deterministic: the same seed always yields the same list.
    """

    @staticmethod
    def inject(seed: ScenarioSeed) -> tuple[StressVector, ...]:
        # Simple deterministic mapping based on seed hash modulo some values.
        base = seed.deterministic_hash
        # Determine presence of three stress types.
        hemorrhage = (base % 3) == 0
        airway = (base % 5) == 0
        instrument = (base % 7) == 0
        vectors: list[StressVector] = []
        if hemorrhage:
            vectors.append(StressVector(name="hemorrhage_amplification", magnitude=0.7))
        if airway:
            vectors.append(StressVector(name="airway_obstruction", magnitude=0.5))
        if instrument:
            vectors.append(StressVector(name="instrument_failure", magnitude=0.4))
        return tuple(vectors)
