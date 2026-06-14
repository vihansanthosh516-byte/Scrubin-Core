"""Deterministic meta‑learning engine – records observations derived from reflections.

The engine reads the ``ReflectionState`` and generates immutable ``LearningObservation``
entries, storing them in the world ``LearningState``.  It never influences any other
cognition components; its sole purpose is observational and replay‑safe.
"""

from __future__ import annotations

from dataclasses import replace
from typing import List

from scrubin.core.events import TimelineEvent
from scrubin.world.state import WorldState
from scrubin.cognition.reflection_state import ReflectionState
from scrubin.cognition.learning_state import LearningState, LearningObservation


class MetaLearningEngine:
    """Engine that evolves the deterministic learning memory.

    The ``evolve`` method is called after the ``ReflectionEngine`` and before
    the multi‑agent runtime.  It produces ``LearningObservation`` records for each
    new ``DecisionReflection`` and updates the ``LearningState`` accordingly.
    """

    def __init__(self, rng):
        # ``rng`` retained for API compatibility – currently unused.
        self.rng = rng

    def evolve(self, world: WorldState) -> WorldState:
        # Retrieve current sub‑states, falling back to defaults if missing.
        learning_state: LearningState = getattr(world, "learning_state", LearningState())
        reflection_state: ReflectionState = getattr(world, "reflection_state", ReflectionState())

        existing_ids = {obs.id for obs in learning_state.observations}
        new_events: List[TimelineEvent] = []

        # Generate a deterministic observation for each reflection that does not yet have one.
        for refl in reflection_state.reflections:
            obs_id = f"learn_{refl.id}"
            if obs_id in existing_ids:
                continue
            # Map reflection fields onto observation fields deterministically.
            observation = LearningObservation(
                id=obs_id,
                tick=world.tick,
                source_reflection_id=refl.id,
                category=refl.outcome,
                lesson=", ".join(refl.reason_tags),  # join tags into a short lesson string
                confidence=refl.confidence,
                severity=refl.stability_score,
                tags=tuple(sorted(refl.reason_tags)),
            )
            learning_state = learning_state.add_observation(observation)
            new_events.append(TimelineEvent(tick=world.tick, description=f"learning_observation_created:{obs_id}"))

        # Update the learning tick to the current world tick.
        learning_state = learning_state.with_learning_tick(world.tick)
        new_events.append(TimelineEvent(tick=world.tick, description=f"learning_tick_updated:{world.tick}"))

        # Apply updated learning state and emit accumulated events.
        world = world.with_learning_state(learning_state)
        # Batch append timeline events.
        world = world.append_timeline(new_events) if new_events else world
        return world
