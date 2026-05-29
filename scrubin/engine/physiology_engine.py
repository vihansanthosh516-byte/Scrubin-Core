"""Simple physiology engine wrapper.

This helper provides a concise API for applying ``VitalDelta`` objects to the
simulation world and for querying the current vitals.  It is deliberately thin
so that existing world evolution logic remains untouched – the engine merely
mutates the ``world.physiology.vitals`` dictionary.
"""

from __future__ import annotations

from scrubin.models.types import VitalDelta
from scrubin.world.state import WorldState


class PhysiologyEngine:
    """Utility for reading and mutating patient vitals.

    Parameters
    ----------
    world: Any
        The simulation world (instance of :class:`scrubin.world.model.SimulationWorld`).
    """

    def __init__(self, world) -> None:
        self.world = world

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------
    def get_vitals(self) -> dict:
        """Return a shallow copy of the current vitals dictionary."""
        # ``world.physiology.vitals`` is mutable; callers should not modify the
        # returned dict directly to avoid accidental side‑effects.
        return dict(self.world.physiology.vitals)

    # ------------------------------------------------------------------
    # Mutation helpers
    # ------------------------------------------------------------------
    def apply_delta(self, delta: VitalDelta) -> None:
        """Add a :class:`VitalDelta` to the world vitals.

        The delta is added element‑wise; missing keys are treated as zero.
        """
        vitals = self.world.physiology.vitals
        for key, value in delta.to_dict().items():
            vitals[key] = vitals.get(key, 0.0) + value

    def tick(self, world: WorldState) -> WorldState:
        """Placeholder tick – currently returns the world unchanged.

        Future extensions can incorporate deterministic physiology evolution (e.g.,
        natural decay, disease progression) while preserving immutability.
        """
        return world
