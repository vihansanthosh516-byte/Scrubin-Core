"""Planner interface exposing deterministic executive decisions.

The planner consumes **only** the immutable ``ExecutivePolicyDecision`` objects
produced by the cognition stack.  This thin wrapper isolates the planner from
the rest of the stack, guaranteeing it cannot inadvertently mutate any lower‑
level stores.
"""

from __future__ import annotations

from typing import Optional

from scrubin.core.orchestrator import Orchestrator
from scrubin.cognition.executive_policy_decision import ExecutivePolicyDecision


def get_latest_policy_decision(orchestrator: Orchestrator) -> Optional[ExecutivePolicyDecision]:
    """Return the most recent ``ExecutivePolicyDecision`` or ``None`` if none exist.

    The function queries ``orchestrator.executive_policy_store`` which stores
    decisions in deterministic insertion order.
    """
    decisions = orchestrator.executive_policy_store.decisions
    return decisions[-1] if decisions else None
