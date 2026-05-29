"""Placeholder equipment engine for operative actors.

Models instrument readiness, monitor status, and equipment failures.  The
current deterministic implementation simply returns the world unchanged.
"""

from __future__ import annotations

from scrubin.world.state import WorldState


class EquipmentEngine:
    def __init__(self, rng) -> None:
        self.rng = rng

    def update(self, world: WorldState) -> WorldState:
        return world
