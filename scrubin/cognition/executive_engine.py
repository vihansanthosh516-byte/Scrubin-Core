"""Deterministic executive engine – generates/updates executive goals.

The engine examines plans, meta‑patterns and beliefs to produce deterministic
goals that guide the autonomous executive layer.
"""

from __future__ import annotations

from typing import Tuple

from .executive_goal import ExecutiveGoal
from .executive_store import ExecutiveStore
from .priority_engine import compute_priority
from .meta_store import MetaStore
from .belief_store import BeliefStore
from scrubin.planner.plan_store import PlanStore


def update_executive(
    meta_store: MetaStore,
    belief_store: BeliefStore,
    plan_store: PlanStore,
    executive_store: ExecutiveStore,
) -> None:
    """Generate deterministic executive goals from the current cognition stack.

    For each plan, a goal is created with supporting meta‑patterns and beliefs.
    The goal's ``priority`` is computed via :func:`compute_priority` using the
    plan's score, confidence and a normalized support factor.
    """
    # Gather supporting meta‑patterns and beliefs (deterministic ordering).
    meta_ids = tuple(p.id for p in meta_store.patterns)
    belief_ids = tuple(b.id for b in belief_store.beliefs)
    total_meta = len(meta_ids) or 1  # avoid division by zero

    for plan in plan_store.plans:
        # Simple deterministic support: all meta‑patterns support every plan.
        supporting_patterns = meta_ids
        supporting_beliefs = belief_ids
        support_norm = len(supporting_patterns) / total_meta

        # Priority combines plan score, confidence and support.
        priority = compute_priority(plan, plan.confidence, support_norm)

        description = f"Goal for plan {plan.id}"
        goal = ExecutiveGoal.create(
            description=description,
            priority=priority,
            confidence=plan.confidence,
            status="pending",
            supporting_patterns=supporting_patterns,
            supporting_beliefs=supporting_beliefs,
            created_tick=plan.root_tick,
        )
        executive_store.add_or_update(goal)
