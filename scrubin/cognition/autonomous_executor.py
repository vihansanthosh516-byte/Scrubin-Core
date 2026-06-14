"""Autonomous executor for the deterministic cognition cycle.

Provides a thin wrapper that advances the orchestrator by one tick and returns
the immutable policy decisions ready for consumption by the planner.
"""

from __future__ import annotations

from typing import List

from scrubin.core.orchestrator import Orchestrator
from scrubin.cognition.executive_policy_decision import ExecutivePolicyDecision
from scrubin.cognition.autonomous_cognitive_os import run_autonomous_cognitive_cycle


def execute_cognition_tick(orchestrator: Orchestrator) -> List[ExecutivePolicyDecision]:
    """Advance the deterministic cognition pipeline by one tick.

    The function internally calls ``run_autonomous_cognitive_cycle`` which
    triggers ``orchestrator.tick()`` and returns the list of ``ExecutivePolicyDecision``
    objects generated for this tick.
    """
    return run_autonomous_cognitive_cycle(orchestrator)
