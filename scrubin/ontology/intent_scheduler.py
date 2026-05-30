from __future__ import annotations

"""Deterministic intent scheduling engine.

The scheduler reads the current ``IntentGraph`` and produces an
``IntentSchedule``.  In this deterministic stub all pending intents are treated as
executable; more sophisticated blocking logic can be added later.
"""

from typing import List

from scrubin.world.state import WorldState, TimelineEvent
from scrubin.ontology.intent_graph import IntentGraph
from scrubin.ontology.intent_schedule import IntentSchedule


class IntentScheduler:
    """Create a deterministic execution schedule from the intent graph.

    * Pending intents (``completion_state == "pending"``) become executable.
    * No intents are blocked or deferred in the minimal implementation.
    """

    def __init__(self, rng) -> None:
        self.rng = rng

    def schedule(self, world: WorldState) -> WorldState:
        intent_graph: IntentGraph = getattr(world, "intent_graph", IntentGraph())
        pending = intent_graph.pending_intents()
        executable_ids = tuple(node.intent_id for node in pending)

        schedule = IntentSchedule(
            executable_intents=executable_ids,
            blocked_intents=tuple(),
            deferred_intents=tuple(),
            interrupted_intents=tuple(),
            schedule_tick=world.tick,
        )
        events: List[TimelineEvent] = []
        if executable_ids:
            events.append(TimelineEvent(world.tick, "intent_generated"))

        new_world = world.with_intent_schedule(schedule)
        for ev in events:
            new_world = new_world.append_timeline(ev)
        return new_world
