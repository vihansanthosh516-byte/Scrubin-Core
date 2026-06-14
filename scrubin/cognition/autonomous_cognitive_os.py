"""Autonomous Cognitive Operating System (ACOS) entry point.

Provides a single deterministic function that runs a full cognition cycle for a
given ``Orchestrator`` instance and returns the resulting executive policy
decisions. All lower‑level cognition steps are performed by the orchestrator’s
``tick`` method; this wrapper merely orchestrates the call order and surface
the final decisions to the planner.
"""

from __future__ import annotations

from typing import List

from scrubin.core.orchestrator import Orchestrator
from scrubin.cognition.executive_policy_decision import ExecutivePolicyDecision


def run_autonomous_cognitive_cycle(orchestrator: Orchestrator) -> List[ExecutivePolicyDecision]:
    """Execute one deterministic cognitive tick and return policy decisions.

    The function triggers ``orchestrator.tick()`` which runs the entire
    deterministic pipeline (events → executive policy arbitration).  After the
    tick completes, the list of immutable ``ExecutivePolicyDecision`` objects
    stored in ``orchestrator.executive_policy_store`` is returned.
    """
    # The orchestrator handles all deterministic state updates.
    orchestrator.tick()
    # The decisions are stored deterministically in insertion order.
    return list(orchestrator.executive_policy_store.decisions)
