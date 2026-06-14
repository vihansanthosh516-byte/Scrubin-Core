"""Deterministic complication event generator.

This module provides ``generate_complication_events`` which scans the hidden state
and other world attributes to produce deterministic ``SurgicalEvent`` objects
representing new complications.  The function **does not mutate** the supplied
``WorldState`` – it merely returns events that the orchestrator will enqueue and
process via the ``event_processor``.
"""

from __future__ import annotations

from typing import List

from scrubin.world.state import WorldState
from scrubin.models.types import ComplicationState
from scrubin.events.event import SurgicalEvent
from scrubin.events.event_types import COMPLICATION_EVENT
from scrubin.core.events import TimelineEvent


def generate_complication_events(world: WorldState) -> List[SurgicalEvent]:
    """Generate deterministic complication events for the current tick.

    The function examines ``world.hidden_state`` and other relevant signals to
    decide whether a new complication should be emitted.  It is pure – the
    ``world`` argument is never mutated.

    Parameters
    ----------
    world:
        The immutable ``WorldState`` snapshot for the current tick.

    Returns
    -------
    List[SurgicalEvent]
        A list of ``SurgicalEvent`` objects, each representing a newly
        detected complication.  If no complications are detected, an empty list
        is returned.
    """
    events: List[SurgicalEvent] = []
    tick = world.tick
    idx = 0

    # Helper to create a complication event and corresponding payload.
    def _make_event(comp_id: str, severity: str, source: str) -> SurgicalEvent:
        payload = {
            "complication": comp_id,
            "severity": severity,
            "source": source,
        }
        return SurgicalEvent(
            event_id=f"{tick}-comp-{idx}",
            event_type=COMPLICATION_EVENT,
            source="complication_engine",
            tick=tick,
            priority=0,
            payload=payload,
        )

    # Currently no deterministic complication triggers are defined for the immutable
    # ``WorldState``.  This function returns an empty list, preserving the existing
    # simulation behaviour.  Future triggers (e.g., based on hidden effects or
    # physiological thresholds) can be added here.
    #
    # Example placeholder logic (commented out) shows how to emit a complication:
    #
    # if False:
    #     events.append(_make_event("example_complication", "moderate", "example_source"))
    #     idx += 1

    return events
