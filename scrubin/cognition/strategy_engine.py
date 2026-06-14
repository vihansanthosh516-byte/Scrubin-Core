"""Deterministic strategy extraction engine.

Scans completed plans and executive goals to discover repeatable action sequences.
No machine‑learning, no randomness – purely based on exact matching of plan
steps and executive outcome status.
"""

from __future__ import annotations

from typing import Tuple, List, Dict

from .strategy import Strategy
from .strategy_store import StrategyStore
from scrubin.planner.plan import Plan
from .executive_store import ExecutiveStore


def _extract_action_sequence(plan: Plan) -> Tuple[str, ...]:
    """Return the ordered tuple of action names from a ``Plan``.
    """
    return tuple(step.action_name for step in plan.steps)


def _find_executive_status_for_plan(plan_id: str, executive_store: ExecutiveStore) -> Tuple[int, int]:
    """Count successes and failures for a given plan based on executive goals.

    A goal is considered a success if its description ends with the plan_id and its
    status is ``completed``. Any other status counts as a failure.
    """
    success = 0
    failure = 0
    for goal in executive_store.goals:
        # ExecutiveGoal description created as "Goal for plan {plan.id}" in the engine.
        if goal.description.strip().endswith(plan_id):
            if goal.status == "completed":
                success += 1
            else:
                failure += 1
    return success, failure


def update_strategies(
    plan_store: "scrubin.planner.plan_store.PlanStore",
    executive_store: ExecutiveStore,
    strategy_store: StrategyStore,
) -> None:
    """Discover deterministic strategies from completed plans.

    The function aggregates plans that share identical action sequences, merges their
    supporting plan IDs, and updates success/failure tallies based on executive goal
    outcomes. New ``Strategy`` objects are added to ``strategy_store`` via its
    ``add_or_update`` method.
    """
    # Group plans by action sequence
    seq_groups: Dict[Tuple[str, ...], List[Plan]] = {}
    for plan in plan_store.plans:
        seq = _extract_action_sequence(plan)
        seq_groups.setdefault(seq, []).append(plan)

    for seq, plans in seq_groups.items():
        # Aggregate data across plans sharing the same sequence
        supporting_ids = set()
        total_success = 0
        total_failure = 0
        first_tick = None
        last_tick = None
        for plan in plans:
            supporting_ids.add(plan.id)
            success, failure = _find_executive_status_for_plan(plan.id, executive_store)
            total_success += success
            total_failure += failure
            plan_start = plan.root_tick
            plan_end = plan.root_tick + plan.horizon
            if first_tick is None or plan_start < first_tick:
                first_tick = plan_start
            if last_tick is None or plan_end > last_tick:
                last_tick = plan_end
        # Determine confidence using deterministic formula
        conf = (total_success + 1) / (total_success + total_failure + 2) if (total_success + total_failure + 2) > 0 else 0.0
        # Build a human‑readable name and description
        name = "Strategy: " + " → ".join(seq) if seq else "Empty Strategy"
        description = f"Derived from {len(plans)} plan(s) with identical action sequence."
        strategy = Strategy.create(
            name=name,
            description=description,
            trigger_conditions=(),
            action_sequence=seq,
            success_count=total_success,
            failure_count=total_failure,
            confidence=conf,
            supporting_plan_ids=tuple(sorted(supporting_ids)),
            first_seen_tick=first_tick or 0,
            last_seen_tick=last_tick or 0,
        )
        strategy_store.add_or_update(strategy)
