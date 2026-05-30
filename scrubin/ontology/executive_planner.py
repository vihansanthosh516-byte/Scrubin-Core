from __future__ import annotations

"""Deterministic executive planning engine.

The planner converts high‑level strategic goals into a concrete ``IntentGraph``.
For the purposes of this integration stub we generate a minimal graph when one
does not already exist and emit a single ``intent_generated`` timeline event.
"""

from typing import List

from scrubin.world.state import WorldState, TimelineEvent
from scrubin.ontology.intent_graph import IntentGraph, IntentNode


class ExecutivePlanner:
    """Create or update the procedural ``IntentGraph``.

    The full strategic planning logic is outside the scope of the current
    patch – a deterministic placeholder suffices to keep the pipeline functional.
    """

    def __init__(self, rng) -> None:
        self.rng = rng

    def plan(self, world: WorldState) -> WorldState:
        intent_graph: IntentGraph = getattr(world, "intent_graph", IntentGraph())
        events: List[TimelineEvent] = []

        if not intent_graph.intents:
            # Create a single root intent as a placeholder.
            root_intent = IntentNode(intent_id="root_intent")
            intent_graph = intent_graph.add_intent(root_intent)
            events.append(TimelineEvent(world.tick, "intent_generated"))

        new_world = world.with_intent_graph(intent_graph)
        for ev in events:
            new_world = new_world.append_timeline(ev)
        return new_world
