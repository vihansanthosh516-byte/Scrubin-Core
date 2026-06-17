"""OrchestrationEngine – coordinates a deterministic tick.
The engine performs the full orchestration pipeline for a single tick:
1️⃣ Integrate subsystem snapshots.
2️⃣ Build a deterministic execution plan.
3️⃣ (Execution is a pure transformation – no side‑effects).
4️⃣ Verify deterministic replay consistency.
5️⃣ Assemble an ``OrchestrationSnapshot``.
All steps are pure functions; no mutation of inputs occurs.
"""

from __future__ import annotations

from typing import Any, Tuple

from .integration_engine import SystemIntegrationEngine
from .execution_engine import ExecutionEngine
from .models import (
    OrchestrationSnapshot,
    IntegrationReport,
    ReplayVerification,
)


class OrchestrationEngine:
    @staticmethod
    def _verify(cross: Any, plan: Any) -> ReplayVerification:
        """Deterministically verify that the execution plan matches the cross‑layer snapshot.

        Currently this engine performs a trivial verification: if a snapshot provides a
        ``deterministic_hash`` attribute, we consider the step valid.  The function never
        mutates inputs and always returns a successful verification when no obvious
        missing hash is detected.
        """
        issues: Tuple[str, ...] = ()
        for step in plan.steps:
            snap = getattr(cross, f"{step.name}_snapshot", None)
            if snap is not None and not hasattr(snap, "deterministic_hash"):
                issues = (*issues, f"no_hash:{step.name}")
        passed = len(issues) == 0
        return ReplayVerification(issues=issues, verification_passed=passed)

    @staticmethod
    def orchestrate(
        learning_snapshot: Any = None,
        adaptive_snapshot: Any = None,
        meta_snapshot: Any = None,
        simulation_snapshot: Any = None,
        scenario_snapshot: Any = None,
        evaluation_snapshot: Any = None,
        stabilization_snapshot: Any = None,
    ) -> OrchestrationSnapshot:
        """Run the full deterministic orchestration for a tick.

        Returns an immutable ``OrchestrationSnapshot`` containing all intermediate
        artefacts.
        """
        # 1️⃣ Integration
        cross, integration_report = SystemIntegrationEngine.integrate(
            learning_snapshot=learning_snapshot,
            adaptive_snapshot=adaptive_snapshot,
            meta_snapshot=meta_snapshot,
            simulation_snapshot=simulation_snapshot,
            scenario_snapshot=scenario_snapshot,
            evaluation_snapshot=evaluation_snapshot,
            stabilization_snapshot=stabilization_snapshot,
        )
        # 2️⃣ Execution plan construction
        plan, trace = ExecutionEngine.build_plan(cross)
        # 3️⃣ Verification
        verification = OrchestrationEngine._verify(cross, plan)
        # 4️⃣ Assemble snapshot
        return OrchestrationSnapshot(
            cross_layer=cross,
            execution_plan=plan,
            execution_trace=trace,
            integration_report=integration_report,
            replay_verification=verification,
        )
