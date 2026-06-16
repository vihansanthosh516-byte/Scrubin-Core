'''Deterministic adaptive planner.

The ``AdaptivePlanner`` builds an ``AdaptivePlan`` from a collection of inputs.
For the purposes of this phase we provide a deterministic placeholder that always
produces a fixed symbolic action sequence. The sequence mirrors the examples
listed in the specification and is ordered by increasing priority.
''' 

from __future__ import annotations

from typing import Iterable, Tuple, Any

from .models import AdaptiveAction, AdaptivePlan, PolicyCandidate


class AdaptivePlanner:
    """Create a deterministic adaptive surgical plan.

    ``plan`` consumes arbitrary context objects (workflow state, physiology,
    anatomy, executive goals, complications, recovery plan, and learned policies).
    The implementation extracts any ``PolicyCandidate`` objects supplied via the
    ``policy_candidates`` argument and appends a canonical set of symbolic
    actions. The result is an ``AdaptivePlan`` instance with a stable ordering.
    """

    def __init__(self) -> None:
        pass

    def build_plan(
        self,
        workflow_state: Any = None,
        physiology: Any = None,
        anatomy: Any = None,
        executive_goals: Any = None,
        complications: Any = None,
        recovery_plan: Any = None,
        learned_policies: Iterable[PolicyCandidate] = (),
    ) -> AdaptivePlan:
        """Generate a deterministic ``AdaptivePlan``.

        The method does not perform any stochastic reasoning – it simply combines
        any provided ``PolicyCandidate`` objects with a static, ordered list of
        ``AdaptiveAction`` symbols.
        """
        # Static symbolic actions – follow the example order.
        static_actions = [
            AdaptiveAction(action_id="obtain_exposure", description="obtain exposure", priority=0),
            AdaptiveAction(action_id="clip_vessel", description="clip vessel", priority=1),
            AdaptiveAction(action_id="convert_approach", description="convert approach", priority=2),
            AdaptiveAction(action_id="suction_field", description="suction field", priority=3),
            AdaptiveAction(action_id="repair_injury", description="repair injury", priority=4),
            AdaptiveAction(action_id="improve_perfusion", description="improve perfusion", priority=5),
            AdaptiveAction(action_id="call_assistance", description="call assistance", priority=6),
        ]

        # Ensure any external policies are deterministically ordered using the
        # ``PolicyCandidate`` ordering contract.
        policy_candidates = tuple(sorted(learned_policies, key=lambda c: (-c.priority, -c.confidence, c.policy_id)))

        # Build the plan – actions are already in a deterministic priority order.
        plan = AdaptivePlan(plan_id="adaptive_plan", actions=tuple(static_actions), policy_candidates=policy_candidates)
        return plan
