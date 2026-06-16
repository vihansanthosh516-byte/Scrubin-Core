"""Meta‑orchestration manager – deterministic supervisory tick.

The ``MetaManager`` coordinates the validation, invariant checking, deterministic
reconciliation and orchestration plan creation for a single simulation tick.
All operations are pure – they use ``dataclasses.replace`` and return new
immutable objects.  No randomness, timestamps or external side‑effects are introduced.
"""

from __future__ import annotations

from .consistency_engine import ConsistencyEngine
from .invariant_engine import InvariantEngine
from .reconciliation_engine import ReconciliationEngine
from .orchestration_engine import OrchestrationEngine
from .models import MetaSnapshot


class MetaManager:
    """Deterministic supervisory control plane.

    ``tick`` receives the full world/state object (e.g. ``WorldState``) and
    returns a ``MetaSnapshot`` containing deterministic reports and an
    execution plan.  The original *state* is never mutated – a new state is
    produced only by the deterministic reconciliation step.
    """

    @staticmethod
    def tick(state: object) -> MetaSnapshot:
        # 1. Consistency validation
        consistency = ConsistencyEngine.validate(state)
        # 2. Invariant checking
        invariants = InvariantEngine.check(state)
        # 3. Deterministic reconciliation (may modify the state)
        reconciled_state = ReconciliationEngine.resolve(consistency, state)
        # 4. Build deterministic orchestration plan (order is fixed)
        plan = OrchestrationEngine.build_plan(reconciled_state)
        # 5. Execution trace (mirrors plan in this simple implementation)
        trace = OrchestrationEngine.trace_execution(plan)
        # 6. Assemble the immutable snapshot
        return MetaSnapshot(
            state=reconciled_state,
            consistency_report=consistency,
            invariant_check=invariants,
            orchestration_plan=plan,
            execution_trace=trace,
        )
