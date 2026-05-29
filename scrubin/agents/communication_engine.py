"""Placeholder communication engine for operative actors.

A full implementation would model requests, acknowledgements, missed
communications, escalation, and closed‑loop feedback.  The current stub
provides a deterministic ``propagate`` method that returns the world unchanged.
"""

from __future__ import annotations

from scrubin.world.state import WorldState


class CommunicationEngine:
    def __init__(self, rng) -> None:
        self.rng = rng

    def propagate(self, world: WorldState) -> WorldState:
        return world
