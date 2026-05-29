"""Inflammatory cascade engine placeholder.

A full implementation would model cytokine activation, local vs systemic
inflammation, edema, capillary leak, and escalation logic.  The current stub
provides a deterministic ``evolve`` method that returns the input state
unchanged – it exists to satisfy imports and can be extended later.
"""

from __future__ import annotations

from scrubin.biology.state import SystemsBiologyState


class InflammationEngine:
    """Placeholder for the inflammatory cascade model.

    The ``evolve`` method is deliberately a no‑op – it simply returns the
    ``SystemsBiologyState`` unchanged.  Deterministic evolution is handled by
    :class:`scrubin.engine.systems_biology_engine.SystemsBiologyEngine`.
    """

    def __init__(self, rng):
        self.rng = rng

    def evolve(self, bio: SystemsBiologyState) -> SystemsBiologyState:
        return bio
