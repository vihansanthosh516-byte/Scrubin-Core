"""GlobalOrchestrator – the deterministic kernel that runs ticks and keeps immutable history.
The orchestrator never mutates its internal state; each operation returns a new
instance with an extended history tuple.  This mirrors the design of earlier
phases (e.g., AdaptiveManager, MetaManager) and guarantees replay safety.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Callable, Tuple

from .orchestration_engine import OrchestrationEngine
from .models import OrchestrationSnapshot


@dataclass(frozen=True, slots=True)
class GlobalOrchestrator:
    """Immutable manager for deterministic global orchestration.

    ``history`` records every ``OrchestrationSnapshot`` produced during the run.
    """

    history: Tuple[OrchestrationSnapshot, ...] = field(default_factory=tuple)

    # ---------------------------------------------------------------------
    # Public API – deterministic tick execution
    # ---------------------------------------------------------------------
    def run_tick(
        self,
        learning_snapshot: Any = None,
        adaptive_snapshot: Any = None,
        meta_snapshot: Any = None,
        simulation_snapshot: Any = None,
        scenario_snapshot: Any = None,
        evaluation_snapshot: Any = None,
        stabilization_snapshot: Any = None,
    ) -> "GlobalOrchestrator":
        """Execute a single deterministic tick and return a new orchestrator.

        The method forwards all provided snapshots to ``OrchestrationEngine``.
        The returned ``GlobalOrchestrator`` contains the previous history plus the
        newly generated ``OrchestrationSnapshot``.
        """
        snapshot = OrchestrationEngine.orchestrate(
            learning_snapshot=learning_snapshot,
            adaptive_snapshot=adaptive_snapshot,
            meta_snapshot=meta_snapshot,
            simulation_snapshot=simulation_snapshot,
            scenario_snapshot=scenario_snapshot,
            evaluation_snapshot=evaluation_snapshot,
            stabilization_snapshot=stabilization_snapshot,
        )
        new_history = self.history + (snapshot,)
        return replace(self, history=new_history)

    # ---------------------------------------------------------------------
    # Convenience runner for a multi‑tick simulation
    # ---------------------------------------------------------------------
    def run_simulation(
        self,
        ticks: int,
        snapshot_factory: Callable[[int], dict[str, Any]],
    ) -> "GlobalOrchestrator":
        """Run *ticks* deterministic ticks using ``snapshot_factory``.

        ``snapshot_factory`` is called with the current tick index (starting at 0)
        and must return a dictionary mapping the snapshot argument names accepted by
        ``run_tick``.
        """
        orchestrator: GlobalOrchestrator = self
        for i in range(ticks):
            args = snapshot_factory(i)
            orchestrator = orchestrator.run_tick(**args)
        return orchestrator

    # ---------------------------------------------------------------------
    # Replay verification across the stored history
    # ---------------------------------------------------------------------
    def verify_replay(self) -> bool:
        """Return ``True`` if all stored snapshots passed their replay verification.
        """
        return all(snap.replay_verification.verification_passed for snap in self.history)
