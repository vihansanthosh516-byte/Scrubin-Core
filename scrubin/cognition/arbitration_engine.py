"""Deterministic cognitive arbitration engine.

The engine detects pairwise conflicts between active goals, creates
``GoalConflict`` objects, resolves them deterministically based on a scoring
function, and propagates the results to the goal hierarchy and intent layer.
All operations are pure and return a new ``WorldState``.
"""

from __future__ import annotations

from dataclasses import replace
from typing import List

from scrubin.core.events import TimelineEvent
from scrubin.world.state import WorldState
from scrubin.cognition.goal_conflict import GoalConflict, GoalConflictState
from scrubin.cognition.goal_state import GoalHierarchyState, GoalNode
from scrubin.cognition.intentive_state import IntentiveCognitionState, AutonomousIntent


class CognitiveArbitrationEngine:
    """Pure functional engine that arbitrates goal conflicts.

    The engine runs after goal management and before intent synthesis.  It
    detects conflicts, creates ``GoalConflict`` objects, resolves them using a
    deterministic scoring function, updates the ``GoalHierarchyState`` and
    ``IntentiveCognitionState`` (pruning intents that reference losing goals),
    and emits deterministic timeline events.
    """

    def __init__(self, rng):
        # ``rng`` retained for API compatibility – not used to preserve
        # deterministic behavior.
        self.rng = rng

    # ---------------------------------------------------------------------
    # Helper – generate deterministic conflict identifier
    # ---------------------------------------------------------------------
    @staticmethod
    def _conflict_id(goal_a_id: str, goal_b_id: str, tick: int) -> str:
        # deterministic ordering by id ensures stable identifiers
        a, b = sorted((goal_a_id, goal_b_id))
        return f"conflict_{a}_{b}_{tick}"

    # ---------------------------------------------------------------------
    # Main evolve method
    # ---------------------------------------------------------------------
    def evolve(self, world: WorldState) -> WorldState:
        # Retrieve current states (fallback defaults if missing)
        goal_state: GoalHierarchyState = getattr(world, "goal_hierarchy_state", GoalHierarchyState())
        intent_state: IntentiveCognitionState = getattr(world, "intentive_cognition_state", IntentiveCognitionState())
        conflict_state: GoalConflictState = getattr(world, "goal_conflict_state", GoalConflictState())

        events: List[TimelineEvent] = []
        prior_dominant_goal_id = goal_state.dominant_goal.id if goal_state.dominant_goal else None
        prior_dominant_intent_id = intent_state.dominant_intent.id if intent_state.dominant_intent else None

        # ---------------------------------------------------------------
        # Step 1 – Detect conflicts between active goals
        # ---------------------------------------------------------------
        active_goals = goal_state.active_goals
        for i, g1 in enumerate(active_goals):
            for g2 in active_goals[i + 1 :]:
                # Overlap in required concepts -> conflict
                if set(g1.required_concepts) & set(g2.required_concepts):
                    conflict_type = "concept"
                # Overlap in blocking conditions -> conflict
                elif set(g1.blocking_conditions) & set(g2.blocking_conditions):
                    conflict_type = "blocking"
                else:
                    continue
                cid = self._conflict_id(g1.id, g2.id, world.tick)
                conflict = GoalConflict(
                    id=cid,
                    goal_a_id=g1.id,
                    goal_b_id=g2.id,
                    conflict_type=conflict_type,
                    severity=1.0,
                    description=f"Conflict between {g1.id} and {g2.id}",
                    detected_tick=world.tick,
                )
                conflict_state = conflict_state.add_conflict(conflict)
                events.append(
                    TimelineEvent(tick=world.tick, description=f"goal_conflict_detected:{conflict.id}")
                )

        # ---------------------------------------------------------------
        # Step 2 – Resolve each active conflict deterministically
        # ---------------------------------------------------------------
        # Ensure conflict_state knows the current arbitration tick before resolution
        conflict_state = conflict_state.with_arbitration_tick(world.tick)
        for conflict in list(conflict_state.active_conflicts):
            # Retrieve the two goals (skip if any missing – may have been abandoned earlier)
            g_a = next((g for g in goal_state.active_goals if g.id == conflict.goal_a_id), None)
            g_b = next((g for g in goal_state.active_goals if g.id == conflict.goal_b_id), None)
            if not g_a or not g_b:
                # If one goal is already gone, just resolve the conflict
                conflict_state = conflict_state.resolve_conflict(conflict.id)
                events.append(
                    TimelineEvent(tick=world.tick, description=f"conflict_resolved:{conflict.id}")
                )
                continue

            # Compute deterministic score for each goal
            def score(goal: GoalNode) -> float:
                return (
                    goal.priority * 2.0
                    + goal.urgency * 1.5
                    + goal.confidence * 1.0
                    - conflict.severity * 2.0
                )

            score_a = score(g_a)
            score_b = score(g_b)
            if score_a > score_b:
                winner, loser = g_a, g_b
            elif score_b > score_a:
                winner, loser = g_b, g_a
            else:
                # Tie – deterministic tie‑break by lexicographic id order
                if g_a.id < g_b.id:
                    winner, loser = g_a, g_b
                else:
                    winner, loser = g_b, g_a

            # -----------------------------------------------------------
            # Apply outcome – abandon loser goal and prune its intents
            # -----------------------------------------------------------
            goal_state = goal_state.abandon_goal(loser.id)
            events.append(
                TimelineEvent(tick=world.tick, description=f"goal_arbitrated:{winner.id}")
            )
            events.append(
                TimelineEvent(tick=world.tick, description=f"goal_suppressed:{loser.id}")
            )

            # Remove intents that belong to the suppressed goal
            new_active_intents = tuple(
                i for i in intent_state.active_intents if i.originating_goal != loser.id
            )
            new_history_intents = tuple(
                i for i in intent_state.intent_history if i.originating_goal != loser.id
            )
            intent_state = IntentiveCognitionState(
                active_intents=tuple(sorted(new_active_intents, key=lambda x: x.id)),
                suppressed_intents=intent_state.suppressed_intents,
                completed_intents=intent_state.completed_intents,
                abandoned_intents=intent_state.abandoned_intents,
                intent_history=tuple(sorted(new_history_intents, key=lambda x: x.id)),
                dominant_intent=None,
                cognitive_tick=intent_state.cognitive_tick,
            )
            intent_state = intent_state.compute_dominant_intent()

            # Resolve conflict record
            conflict_state = conflict_state.resolve_conflict(conflict.id)
            events.append(
                TimelineEvent(tick=world.tick, description=f"conflict_resolved:{conflict.id}")
            )

        # ---------------------------------------------------------------
        # Step 3 – Re‑compute dominant goal after all changes
        # ---------------------------------------------------------------
        goal_state = goal_state.compute_dominant_goal()
        # Emit dominant‑goal shift if changed
        new_dominant_goal_id = goal_state.dominant_goal.id if goal_state.dominant_goal else None
        if prior_dominant_goal_id != new_dominant_goal_id:
            events.append(
                TimelineEvent(tick=world.tick, description=f"dominant_goal_shifted:{new_dominant_goal_id}")
            )
        # Emit dominant‑intent shift if changed
        new_dominant_intent_id = intent_state.dominant_intent.id if intent_state.dominant_intent else None
        if prior_dominant_intent_id != new_dominant_intent_id:
            events.append(
                TimelineEvent(tick=world.tick, description=f"dominant_intent_shifted:{new_dominant_intent_id}")
            )

        # ---------------------------------------------------------------
        # Step 4 – Apply updated sub‑states to the world
        # ---------------------------------------------------------------
        world = world.with_goal_hierarchy_state(goal_state)
        world = world.with_intentive_cognition_state(intent_state)
        world = world.with_goal_conflict_state(conflict_state)
        for ev in events:
            world = world.append_timeline(ev)
        return world
