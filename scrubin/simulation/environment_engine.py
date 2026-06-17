"""Deterministic environment engine.

Applies ``InteractionPacket`` updates to the ``EnvironmentState`` using
pure ``replace`` semantics.  No randomness or side‑effects are introduced.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Tuple

from .models import EnvironmentState, InteractionPacket, SimulationWorld


class EnvironmentEngine:
    """Update the OR environment based on deterministic interaction packets.

    The engine consumes a tuple of ``InteractionPacket`` objects and returns a
    new ``SimulationWorld`` with an updated ``environment`` field.
    """

    @staticmethod
    def apply(world: SimulationWorld, packets: Tuple[InteractionPacket, ...]) -> SimulationWorld:
        env: EnvironmentState = world.environment
        available = list(env.available_instruments)
        # Process packets in deterministic priority order (sorted by priority)
        for pkt in sorted(packets, key=lambda p: p.priority):
            act = pkt.action
            if act.action_type == "request_instrument" and act.target in available:
                # Allocate the instrument – remove it from the available list
                available.remove(act.target)
            # Additional deterministic handling could be added here.
        new_env = replace(env, available_instruments=tuple(sorted(available)))
        return replace(world, environment=new_env)
