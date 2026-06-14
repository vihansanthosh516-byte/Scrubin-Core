"""Deterministic executive monitor – updates goal status based on world state.

The monitor walks through ``ScheduledGoal`` objects and marks them as
``completed`` when the associated plan horizon has elapsed, otherwise they stay
``active``. No mutation of the world occurs; the function merely updates the
``ExecutiveStore``.
"""

from __future__ import annotations
from dataclasses import replace

from typing import List

from .executive_goal import ExecutiveGoal
from .executive_store import ExecutiveStore
from .executive_scheduler import ScheduledGoal
from scrubin.planner.plan_store import PlanStore


def monitor_goals(current_tick: int, executive_store: ExecutiveStore, plan_store: PlanStore, scheduled: List[ScheduledGoal]) -> None:
    """Update goal status deterministically.

    * If ``current_tick`` is greater than or equal to ``scheduled_tick`` plus the
      horizon of the plan referenced by the goal description, the goal is marked
      ``completed``.
    * Otherwise the goal is marked ``active``.

    The function updates the store via ``add_or_update`` which merges the
    status change while preserving deterministic ordering.
    """
    # Helper to extract plan id from the goal description (format: "Goal for plan {plan_id}")
    def extract_plan_id(goal: ExecutiveGoal) -> str:
        parts = goal.description.split()
        return parts[-1] if parts else ""

    # Build a map of plan id -> Plan for quick lookup.
    plan_map = {p.id: p for p in plan_store.plans}

    for sg in scheduled:
        goal = sg.goal
        plan_id = extract_plan_id(goal)
        plan = plan_map.get(plan_id)
        if plan is None:
            # No associated plan – leave status unchanged.
            continue
        horizon = plan.horizon
        if current_tick >= sg.scheduled_tick + horizon:
            new_status = "completed"
        else:
            new_status = "active"
        # Update the goal with the new status.
        updated = ExecutiveGoal(
            id=goal.id,
            description=goal.description,
            priority=goal.priority,
            confidence=goal.confidence,
            status=new_status,
            supporting_patterns=goal.supporting_patterns,
            supporting_beliefs=goal.supporting_beliefs,
            created_tick=goal.created_tick,
            replay_hash="",
        )
        # Preserve deterministic hash.
        from .executive_goal import deterministic_executive_goal_hash
        updated = replace(updated, replay_hash=deterministic_executive_goal_hash(updated))
        executive_store.add_or_update(updated)
