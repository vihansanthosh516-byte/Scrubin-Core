"""Deterministic intent synthesis engine.

The engine runs after overload evolution and enriches the simulation with
autonomous intents.  It updates two parts of the world state:

1. ``intent_graph`` – a new :class:`scrubin.ontology.intent_graph.IntentNode`
   that integrates the generated intent into the procedural execution plan.
2. ``intentive_cognition_state`` – a lightweight container for the synthesized
   :class:`AutonomousIntent` objects and the computed dominant intent.

All operations are pure – a brand‑new ``WorldState`` is returned.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from scrubin.world.state import WorldState
from scrubin.cognition.intentive_state import IntentiveCognitionState, AutonomousIntent
from scrubin.ontology.intent_graph import IntentGraph, IntentNode


@dataclass(frozen=True)
class IntentSynthesisEngine:
    """Pure functional engine that deterministically generates autonomous intents.

    The ``rng`` argument is retained for API compatibility but is not used – the
    engine is fully deterministic to preserve replay safety.
    """

    rng: any

    def _generate_intent(self, world: WorldState) -> AutonomousIntent:
        """Create a deterministic autonomous intent for the current tick.

        The urgency is derived from overload and attention levels, while confidence
        follows a simple deterministic pattern based on the tick parity.
        """
        overload = getattr(world, "overload_state", None)
        attention = getattr(world, "attention_state", None)
        overload_level = overload.overload_level if overload else 0.0
        attention_level = getattr(attention, "attention_level", 0.0) if attention else 0.0

        # Urgency: overload minus attention, clamped to ``[0.0, 1.0]``.
        urgency = max(0.0, min(1.0, overload_level - attention_level))

        # Deterministic confidence: 0.6 on even ticks, 0.8 on odd ticks.
        confidence = 0.6 if world.tick % 2 == 0 else 0.8

        intent_id = f"auto_intent_{world.tick}"
        description = f"Synthesized autonomous intent at tick {world.tick}"
        return AutonomousIntent(
            intent_id=intent_id,
            description=description,
            urgency=urgency,
            confidence=confidence,
        )

    def evolve(self, world: WorldState) -> WorldState:
        """Evolve the world by adding a newly synthesized autonomous intent.

        The function updates both ``intent_graph`` (by inserting a matching
        ``IntentNode``) and ``intentive_cognition_state`` (by storing the
        ``AutonomousIntent`` and recomputing the dominant intent).
        """
        # -----------------------------------------------------------------
        # 1️⃣  Generate the autonomous intent.
        # -----------------------------------------------------------------
        auto_intent = self._generate_intent(world)

        # -----------------------------------------------------------------
        # 2️⃣  Update the IntentiveCognitionState container.
        # -----------------------------------------------------------------
        intentive_state: IntentiveCognitionState = getattr(
            world, "intentive_cognition_state", IntentiveCognitionState()
        )
        intentive_state = intentive_state.add_intent(auto_intent).compute_dominant_intent()

        # -----------------------------------------------------------------
        # 3️⃣  Mirror the intent into the procedural IntentGraph.
        # -----------------------------------------------------------------
        intent_graph: IntentGraph = getattr(world, "intent_graph", IntentGraph())
        intent_node = IntentNode(
            intent_id=auto_intent.intent_id,
            parent_id=None,
            child_ids=tuple(),
            required_concepts=tuple(),
            blocking_conditions=tuple(),
            expected_state="",
            anticipated_complications=tuple(),
            fallback_paths=tuple(),
            confidence=auto_intent.confidence,
            completion_state="pending",
            semantic_priority=int(auto_intent.urgency * 100),
        )
        intent_graph = intent_graph.add_intent(intent_node)

        # -----------------------------------------------------------------
        # 4️⃣  Return the updated world.
        # -----------------------------------------------------------------
        world = world.with_intent_graph(intent_graph)
        world = world.with_intentive_cognition_state(intentive_state)
        return world
