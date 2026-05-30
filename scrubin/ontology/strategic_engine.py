from __future__ import annotations

"""Placeholder strategic engine.

In the full framework this component would process ``StrategicState`` and
generate higher‑level plans.  The deterministic stub simply returns the world
unchanged.
"""

from scrubin.world.state import WorldState


class StrategicEngine:
    def __init__(self, rng) -> None:
        self.rng = rng

    def process(self, world: WorldState) -> WorldState:
        # No transformation – deterministic no‑op.
        return world
