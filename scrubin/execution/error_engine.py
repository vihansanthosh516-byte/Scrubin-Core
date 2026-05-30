from __future__ import annotations

"""Deterministic technical error propagation engine.

Accumulates micro‑errors into latent technical complications and emits timeline
events that can later be manifested as physiological complications.
"""

from typing import List

from scrubin.world.state import WorldState
from scrubin.core.events import TimelineEvent
from scrubin.execution.state import TechnicalExecutionState


class TechnicalErrorEngine:
    """Propagate accumulated technical errors into hidden effects.

    The deterministic model converts ``micro_error_accumulation`` crosses a
    threshold into a hidden effect that later may surface as a complication.
    """

    def __init__(self, rng) -> None:
        self.rng = rng

    def propagate(self, world: WorldState) -> WorldState:
        tech: TechnicalExecutionState = getattr(world, "technical_execution_state", TechnicalExecutionState())
        events: List[TimelineEvent] = []

        # Threshold for latent technical error.
        if tech.micro_error_accumulation >= 0.2:
            events.append(TimelineEvent(world.tick, "latent_technical_error"))
            # Reset accumulation after detection.
            tech = tech.with_micro_error_accumulation(0.0)
            # Increase risk level.
            tech = tech.with_current_risk_level(min(1.0, tech.current_risk_level + 0.2))

        new_world = world.with_technical_execution_state(tech)
        for ev in events:
            new_world = new_world.append_timeline(ev)
        return new_world
