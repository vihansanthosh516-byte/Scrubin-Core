from __future__ import annotations

"""Deterministic cognitive overload engine.

The engine inspects ``AttentionState`` and updates ``OverloadState``.  When the
current load exceeds the configured overload threshold it raises an
``overload_escalation`` event and increments a fatigue‑style overload level.
"""

from typing import List

from scrubin.world.state import WorldState, TimelineEvent
from scrubin.ontology.attention_state import AttentionState
from scrubin.ontology.overload_state import OverloadState


class OverloadEngine:
    """Engine that models deterministic cognitive degradation.

    The logic is intentionally lightweight – it reacts solely to the ``load``
    compared with ``overload_threshold`` from the ``AttentionState``.
    """

    def __init__(self, rng) -> None:
        self.rng = rng

    def evolve(self, world: WorldState) -> WorldState:
        att_state: AttentionState = getattr(world, "attention_state", AttentionState())
        overload_state: OverloadState = getattr(world, "overload_state", OverloadState())
        events: List[TimelineEvent] = []

        if att_state.current_load > att_state.overload_threshold:
            # Increase overload level (clamped).
            new_level = min(1.0, overload_state.overload_level + 0.1)
            new_ticks = overload_state.overload_ticks + 1
            overload_state = overload_state.with_level(new_level).with_ticks(new_ticks)
            events.append(TimelineEvent(world.tick, "overload_escalation"))
        else:
            # Decay overload gradually.
            new_level = max(0.0, overload_state.overload_level - 0.05)
            new_ticks = max(0, overload_state.overload_ticks - 1)
            overload_state = overload_state.with_level(new_level).with_ticks(new_ticks)

        new_world = world.with_overload_state(overload_state)
        # Batch append timeline events (if any).
        new_world = new_world.append_timeline(events) if events else new_world
        return new_world
