"""Deterministic executive scheduler – orders goals for execution.

The scheduler produces a deterministic list of ``ScheduledGoal`` objects sorted
by priority, confidence and goal identifier.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .executive_goal import ExecutiveGoal
from .executive_store import ExecutiveStore


@dataclass(frozen=True)
class ScheduledGoal:
    """A goal scheduled for execution at a specific tick.

    ``scheduled_tick`` – the orchestration tick at which the goal is slated to
    start. ``goal`` – the deterministic ``ExecutiveGoal`` instance.
    """
    goal: ExecutiveGoal
    scheduled_tick: int


def schedule_goals(executive_store: ExecutiveStore, current_tick: int) -> List[ScheduledGoal]:
    """Return a deterministic ordering of pending goals.

    All goals with status ``pending`` are promoted to ``active`` and wrapped in a
    ``ScheduledGoal``. The resulting list is sorted by:

    1. ``priority`` (descending)
    2. ``confidence`` (descending)
    3. ``goal.id`` (lexicographic)

    The function does **not** mutate the original store – status changes are
    applied via ``ExecutiveStore.add_or_update`` by the caller (or a later
    monitoring step).
    """
    pending = executive_store.query(status="pending")
    scheduled: List[ScheduledGoal] = [
        ScheduledGoal(goal=g, scheduled_tick=current_tick) for g in pending
    ]
    # Deterministic sort as required.
    scheduled.sort(key=lambda sg: (-sg.goal.priority, -sg.goal.confidence, sg.goal.id))
    return scheduled
