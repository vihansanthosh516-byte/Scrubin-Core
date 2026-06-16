'''Adaptive manager – orchestrates the deterministic adaptive pipeline.

The manager wires together the components defined in the Phase 8.1 package:
    * ``PolicySelector`` – selects policy candidates.
    * ``AdaptivePlanner`` – builds an ``AdaptivePlan``.
    * ``ActionRanker`` – orders the actions.
    * ``ContingencyEngine`` – generates fallback contingency plans.
    * ``SimulationPreviewEngine`` – predicts the outcome of the plan.

The final product is an ``AdaptiveSnapshot`` that aggregates all intermediate
structures and includes a deterministic aggregate hash for replay safety.
''' 

from __future__ import annotations

from typing import Any, Tuple

from .policy_selector import PolicySelector
from .planner import AdaptivePlanner
from .action_ranker import ActionRanker
from .contingency_engine import ContingencyEngine
from .simulation_preview import SimulationPreviewEngine
from .models import (
    AdaptiveSnapshot,
    AdaptivePlan,
    AdaptiveAction,
    PolicyCandidate,
    ContingencyPlan,
    SimulationPreview,
)


class AdaptiveManager:
    """High‑level deterministic adaptive planning orchestrator.

    ``generate_snapshot`` accepts a dictionary ``context`` that may contain any of
    the inputs required by the individual pipeline stages. Missing keys are
    treated as ``None`` or empty iterables, keeping the operation fully
    deterministic.
    """

    def __init__(self) -> None:
        # Instantiate components once – they have no internal mutable state.
        self.policy_selector = PolicySelector()
        self.planner = AdaptivePlanner()
        self.ranker = ActionRanker()
        self.contingency_engine = ContingencyEngine()
        self.preview_engine = SimulationPreviewEngine()

    def generate_snapshot(self, context: dict[str, Any] | None = None) -> AdaptiveSnapshot:
        """Run the full deterministic adaptive pipeline and return a snapshot.

        ``context`` may provide the following optional keys (all values are
        optional and default to empty placeholders):
            * ``learned_policies`` – iterable of objects for policy selection.
            * ``executive_goals`` – iterable for policy selection.
            * ``executive_decisions`` – iterable for policy selection.
            * ``experience_patterns`` – iterable for policy selection.
            * ``generalized_rules`` – iterable for policy selection.
            * ``knowledge_graph`` – unused placeholder for API compatibility.
            * ``workflow_state`` – opaque object passed to the planner.
            * ``physiology`` – opaque object passed to the planner.
            * ``anatomy`` – opaque object passed to the planner.
            * ``complications`` – opaque object passed to the planner.
            * ``recovery_plan`` – opaque object passed to the planner.
            * ``action_metrics`` – mapping ``action_id`` → metric dict used by the
              ``ActionRanker``.
        """
        ctx = context or {}
        # -------------------------------------------------------------------
        # 1. Policy selection
        # -------------------------------------------------------------------
        selected_candidates: Tuple[PolicyCandidate, ...] = self.policy_selector.select(
            learned_policies=ctx.get("learned_policies", ()),
            executive_goals=ctx.get("executive_goals", ()),
            executive_decisions=ctx.get("executive_decisions", ()),
            experience_patterns=ctx.get("experience_patterns", ()),
            generalized_rules=ctx.get("generalized_rules", ()),
            knowledge_graph=ctx.get("knowledge_graph"),
        )

        # -------------------------------------------------------------------
        # 2. Adaptive planning – incorporate the selected candidates.
        # -------------------------------------------------------------------
        adaptive_plan: AdaptivePlan = self.planner.build_plan(
            workflow_state=ctx.get("workflow_state"),
            physiology=ctx.get("physiology"),
            anatomy=ctx.get("anatomy"),
            executive_goals=ctx.get("executive_goals"),
            complications=ctx.get("complications"),
            recovery_plan=ctx.get("recovery_plan"),
            learned_policies=selected_candidates,
        )

        # -------------------------------------------------------------------
        # 3. Action ranking – deterministic ordering using optional metrics.
        # -------------------------------------------------------------------
        ranked_actions: Tuple[AdaptiveAction, ...] = self.ranker.rank_actions(
            adaptive_plan.actions,
            metrics_by_action=ctx.get("action_metrics", {}),
        )

        # -------------------------------------------------------------------
        # 4. Contingency generation – deterministic set of fallback plans.
        # -------------------------------------------------------------------
        contingency_plans: Tuple[ContingencyPlan, ...] = self.contingency_engine.generate_contingencies(
            adaptive_plan=adaptive_plan
        )

        # -------------------------------------------------------------------
        # 5. Simulation preview – deterministic prediction based on the plan.
        # -------------------------------------------------------------------
        preview: SimulationPreview = self.preview_engine.preview(adaptive_plan)

        # -------------------------------------------------------------------
        # 6. Assemble snapshot with deterministic aggregate hash.
        # -------------------------------------------------------------------
        snapshot = AdaptiveSnapshot(
            snapshot_id="adaptive_snapshot",
            adaptive_plan=adaptive_plan,
            selected_policy_candidates=selected_candidates,
            ranked_actions=ranked_actions,
            contingency_plans=contingency_plans,
            simulation_preview=preview,
        )
        snapshot = snapshot.with_aggregate_hash()
        return snapshot
