from __future__ import annotations

"""Deterministic recovery & salvage planning engine.

The stub examines ``OverloadState`` and, when the overload level exceeds a
threshold, marks a simple ``RecoveryState`` as active and emits a
``salvage_protocol_activated`` event.
"""

from typing import List

from scrubin.world.state import WorldState, TimelineEvent
from scrubin.ontology.overload_state import OverloadState
from scrubin.ontology.recovery_state import RecoveryState


class RecoveryEngine:
    """Detect failing trajectories and generate rescue intents.

    For now the implementation only toggles a boolean flag when overload is high.
    """

    def __init__(self, rng) -> None:
        self.rng = rng

    def recover(self, world: WorldState) -> WorldState:
        overload: OverloadState = getattr(world, "overload_state", OverloadState())
        recovery: RecoveryState = getattr(world, "recovery_state", RecoveryState())
        events: List[TimelineEvent] = []

        if overload.overload_level >= 0.5:
            # Activate salvage protocol.
            recovery = recovery.with_salvage_active(True)
            events.append(TimelineEvent(world.tick, "salvage_protocol_activated"))
        else:
            recovery = recovery.with_salvage_active(False)

        new_world = world.with_recovery_state(recovery)
        for ev in events:
            new_world = new_world.append_timeline(ev)
        return new_world
