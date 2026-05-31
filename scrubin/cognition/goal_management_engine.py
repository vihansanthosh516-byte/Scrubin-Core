"""Goal Management Engine – deterministic goal lifecycle integration.

The engine inspects the current ``WorldState`` and updates the ``GoalHierarchyState``
according to a simple deterministic policy:

* For each active intent without an originating goal, create a matching goal.
* Progress each active goal by a fixed amount (0.1) per tick.
* When progress reaches ``1.0`` the goal is completed.
* Compute the dominant goal using the ordering defined in ``GoalHierarchyState``.
* Emit deterministic timeline events for creation, completion, abandonment and
  dominant‑goal shifts.
"""

from __future__ import annotations

from dataclasses import replace
from typing import List

from scrubin.core.events import TimelineEvent
from scrubin.world.state import WorldState
from scrubin.cognition.goal_state import GoalHierarchyState, GoalNode
from scrubin.cognition.intentive_state import IntentiveCognitionState


class GoalManagementEngine:
    """Pure functional engine that updates the deterministic goal hierarchy.

    The engine does not modify any input objects – it always returns a brand‑new
    ``WorldState``.  All state transitions are deterministic and replay‑safe.
    """

    def __init__(self, rng):
        # ``rng`` retained for API compatibility – not used to preserve determinism.
        self.rng = rng

    def evolve(self, world: WorldState) -> WorldState:
        """Evolve the world by updating the ``GoalHierarchyState``.

        The method performs the following deterministic steps:
        1. Generate missing goals for active intents that lack an originating goal.
        2. Increment progress for all active goals.
        3. Complete goals whose progress reaches ``1.0``.
        4. Compute the dominant goal.
        5. Record a cognition tick.
        6. Emit appropriate timeline events.
        """
        # Retrieve current goal hierarchy (create empty if missing).
        goal_state: GoalHierarchyState = getattr(
            world, "goal_hierarchy_state", GoalHierarchyState()
        )
        intent_state: IntentiveCognitionState = getattr(
            world, "intentive_cognition_state", IntentiveCognitionState()
        )

        events: List[TimelineEvent] = []
        existing_ids = {g.id for g in goal_state.active_goals}

        # -----------------------------------------------------------------
        # 1️⃣ Generate missing goals for intents without an originating goal.
        # -----------------------------------------------------------------
        for intent in intent_state.active_intents:
            if intent.originating_goal is None:
                goal_id = f"goal_{intent.id}"
                if goal_id not in existing_ids:
                    new_goal = GoalNode(
                        id=goal_id,
                        parent_goal_id=None,
                        description=intent.description,
                        priority=0.0,
                        urgency=intent.urgency,
                        confidence=intent.confidence,
                        required_concepts=intent.required_concepts,
                        blocking_conditions=intent.blocking_conditions,
                        created_tick=world.tick,
                    )
                    goal_state = goal_state.add_goal(new_goal)
                    events.append(
                        TimelineEvent(
                            tick=world.tick, description=f"goal_created:{new_goal.id}"
                        )
                    )

        # -----------------------------------------------------------------
        # 2️⃣ Increment progress for all active goals (deterministic step).
        # -----------------------------------------------------------------
        updated_active = tuple(
            g.with_progress(min(1.0, g.progress + 0.1)) for g in goal_state.active_goals
        )
        # Keep deterministic ordering by id.
        goal_state = replace(
            goal_state, active_goals=tuple(sorted(updated_active, key=lambda x: x.id))
        )

        # -----------------------------------------------------------------
        # 3️⃣ Complete goals that have reached full progress.
        # -----------------------------------------------------------------
        completed_ids = [g.id for g in goal_state.active_goals if g.progress >= 1.0]
        for gid in completed_ids:
            goal_state = goal_state.complete_goal(gid)
            events.append(
                TimelineEvent(tick=world.tick, description=f"goal_completed:{gid}")
            )

        # -----------------------------------------------------------------
        # 4️⃣ Compute the dominant goal.
        # -----------------------------------------------------------------
        prior_dominant_id = goal_state.dominant_goal.id if goal_state.dominant_goal else None
        goal_state = goal_state.compute_dominant_goal()
        new_dominant_id = goal_state.dominant_goal.id if goal_state.dominant_goal else None
        if prior_dominant_id != new_dominant_id:
            events.append(
                TimelineEvent(
                    tick=world.tick, description=f"dominant_goal_shifted:{new_dominant_id}"
                )
            )

        # -----------------------------------------------------------------
        # 5️⃣ Record the cognition tick for deterministic replay.
        # -----------------------------------------------------------------
        goal_state = goal_state.with_cognition_tick(world.tick)

        # -----------------------------------------------------------------
        # 6️⃣ Apply updated goal hierarchy to the world and emit events.
        # -----------------------------------------------------------------
        world = world.with_goal_hierarchy_state(goal_state)
        for ev in events:
            world = world.append_timeline(ev)
        return world
