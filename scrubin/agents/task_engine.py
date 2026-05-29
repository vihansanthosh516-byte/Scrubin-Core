"""Placeholder task engine for operative actors.

Manages delegated tasks, queue handling and interruption logic.  The current
implementation is a deterministic no‑op used for integration testing.
"""

from __future__ import annotations

from scrubin.world.state import WorldState


class TaskEngine:
    def __init__(self, rng) -> None:
        self.rng = rng

    def update(self, world: WorldState) -> WorldState:
        return world
