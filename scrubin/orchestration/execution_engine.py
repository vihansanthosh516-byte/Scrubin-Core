"""ExecutionEngine – turns a CrossLayerSnapshot into a deterministic execution plan.
The execution order is fixed and never changes based on data content:
Scenario → Simulation → Meta → Learning → Adaptive → Evaluation → Stabilization.
"""

from __future__ import annotations

from typing import Tuple

from .models import ExecutionPlan, ExecutionStep, ExecutionTrace, CrossLayerSnapshot


class ExecutionEngine:
    @staticmethod
    def build_plan(cross: CrossLayerSnapshot) -> Tuple[ExecutionPlan, ExecutionTrace]:
        """Create a deterministic ``ExecutionPlan`` and ``ExecutionTrace``.

        The plan consists of ``ExecutionStep`` objects for each subsystem in the
        fixed order defined by Phase 8.7.  The trace records just the step names.
        """
        order = [
            ("scenario", cross.scenario_snapshot),
            ("simulation", cross.simulation_snapshot),
            ("meta", cross.meta_snapshot),
            ("learning", cross.learning_snapshot),
            ("adaptive", cross.adaptive_snapshot),
            ("evaluation", cross.evaluation_snapshot),
            ("stabilization", cross.stabilization_snapshot),
        ]
        steps = []
        names = []
        for name, snap in order:
            # Even if a snapshot is ``None`` we still create a step to preserve ordering.
            step = ExecutionStep(name=name, snapshot=snap)
            steps.append(step)
            names.append(name)
        plan = ExecutionPlan(steps=tuple(steps))
        trace = ExecutionTrace(step_names=tuple(names))
        return plan, trace
