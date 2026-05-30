from __future__ import annotations

"""Deterministic procedural workflow runtime.

Converts the high‑level ``IntentGraph`` into a deterministic sequence of
technical maneuvers.  For this stub implementation the workflow simply selects the
first pending intent and records it in the ``TechnicalExecutionState``.
"""

from typing import List

from scrubin.world.state import WorldState
from scrubin.core.events import TimelineEvent
from scrubin.ontology.intent_graph import IntentGraph
from scrubin.execution.state import TechnicalExecutionState


class WorkflowEngine:
    """Create a deterministic execution workflow from intent graph nodes.

    The engine populates ``TechnicalExecutionState.current_maneuver`` with the
    identifier of the next pending intent.  It also tracks a simple history and
    emits a progression event.
    """

    def __init__(self, rng) -> None:
        self.rng = rng

    def process(self, world: WorldState) -> WorldState:
        intent_graph: IntentGraph = getattr(world, "intent_graph", IntentGraph())
        pending = intent_graph.pending_intents()
        tech: TechnicalExecutionState = getattr(world, "technical_execution_state", TechnicalExecutionState())
        events: List[TimelineEvent] = []

        if pending:
            next_intent = pending[0]
            tech = tech.with_current_maneuver(next_intent.intent_id)
            events.append(TimelineEvent(world.tick, f"workflow_progression:{next_intent.intent_id}"))
        else:
            events.append(TimelineEvent(world.tick, "workflow_stalled"))

        new_world = world.with_technical_execution_state(tech)
        for ev in events:
            new_world = new_world.append_timeline(ev)
        return new_world
