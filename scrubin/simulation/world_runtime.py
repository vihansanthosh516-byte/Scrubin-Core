"""Deterministic world runtime for Phase 8.3.

Provides a simple deterministic replay loop: ``run`` executes a specified
number of ticks starting from an initial ``SimulationWorld`` and records the
hash chain.  ``replay`` can be used to verify that a previously recorded hash
sequence reproduces the same final snapshot.
"""

from __future__ import annotations

from typing import List, Tuple

from .simulation_manager import SimulationManager
from .models import SimulationWorld, SimulationSnapshot


class WorldRuntime:
    """Deterministic execution engine for the simulation world.

    * ``run`` advances the simulation a given number of ticks, returning a list
      of ``SimulationSnapshot`` objects.
    * ``replay`` accepts a list of expected snapshot hashes and verifies that
      reproducing the same number of ticks yields an identical hash sequence.
    """

    @staticmethod
    def run(initial_world: SimulationWorld, ticks: int) -> List[SimulationSnapshot]:
        snapshots: List[SimulationSnapshot] = []
        world = initial_world
        for _ in range(ticks):
            snap = SimulationManager.tick(world)
            snapshots.append(snap)
            world = snap.world
        return snapshots

    @staticmethod
    def replay(initial_world: SimulationWorld, expected_hashes: Tuple[int, ...]) -> bool:
        """Execute the simulation and verify that the hash chain matches.

        Returns ``True`` if all hashes match, ``False`` otherwise.
        """
        world = initial_world
        for expected in expected_hashes:
            snap = SimulationManager.tick(world)
            if snap.deterministic_hash != expected:
                return False
            world = snap.world
        return True
