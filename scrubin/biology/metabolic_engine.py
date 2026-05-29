"""Metabolic & oxygen debt engine placeholder.

Provides a deterministic ``evolve`` method that currently performs no
modifications.  Detailed modeling is handled in the unified biological engine.
"""

from __future__ import annotations

from scrubin.biology.state import SystemsBiologyState


class MetabolicEngine:
    def __init__(self, rng):
        self.rng = rng

    def evolve(self, bio: SystemsBiologyState) -> SystemsBiologyState:
        return bio
