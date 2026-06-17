"""Global deterministic stabilization manager.

Orchestrates drift computation, stability assessment, convergence detection,
correction generation and deterministic rollback evaluation.  Returns a
`StabilizationSnapshot` containing all artefacts.
"""

from __future__ import annotations

from .drift_engine import DriftEngine
from .stability_engine import StabilityEngine
from .convergence_engine import ConvergenceEngine
from .correction_engine import CorrectionEngine
from .rollback_engine import RollbackEngine
from .models import StabilizationSnapshot


class StabilizationManager:
    @staticmethod
    def tick(state: any, stable_hashes: tuple[int, ...] = ()) -> StabilizationSnapshot:
        # 1. Compute deterministic drift.
        drift = DriftEngine.compute(state)
        # 2. Assess stability.
        stability = StabilityEngine.assess(drift)
        # 3. Determine convergence status.
        prev_hash = getattr(state, "previous_deterministic_hash", 0)
        curr_hash = getattr(state, "deterministic_hash", 0)
        convergence = ConvergenceEngine.evaluate(prev_hash, curr_hash)
        # 4. Generate correction plan.
        correction_plan = CorrectionEngine.generate(stability.violations)
        # 5. Evaluate rollback requirement.
        rollback = RollbackEngine.evaluate(state, stable_hashes)
        # 6. Assemble final snapshot.
        return StabilizationSnapshot(
            drift=drift,
            stability=stability,
            convergence=convergence,
            correction_plan=correction_plan,
            rollback=rollback,
            original_hash=curr_hash,
        )
