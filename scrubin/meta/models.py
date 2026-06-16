"""Meta‑orchestration immutable dataclasses.
All dataclasses are frozen, use slots, and provide a deterministic_hash
computed via the built‑in ``hash`` of a tuple of their primitive fields.
Collections are stored as immutable ``tuple`` objects and sorted
deterministically where needed.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Tuple, Any


@dataclass(frozen=True, slots=True)
class SystemConsistencyReport:
    """Report of cross‑layer consistency violations.

    ``violations`` is a sorted tuple of strings describing each issue.
    """

    violations: Tuple[str, ...] = ()

    @property
    def deterministic_hash(self) -> int:
        return hash(self.violations)


@dataclass(frozen=True, slots=True)
class CrossLayerValidation:
    """Placeholder for detailed validation data (not used in this simple impl)."""

    details: Tuple[Any, ...] = ()

    @property
    def deterministic_hash(self) -> int:
        return hash(self.details)


@dataclass(frozen=True, slots=True)
class DeterministicInvariantCheck:
    """Result of invariant checking.

    ``issues`` is a sorted tuple of strings.
    """

    issues: Tuple[str, ...] = ()

    @property
    def deterministic_hash(self) -> int:
        return hash(self.issues)


@dataclass(frozen=True, slots=True)
class OrchestrationPlan:
    """Deterministic ordered plan of subsystem execution steps."""

    steps: Tuple[str, ...] = (
        "physiology_update",
        "complication_propagation",
        "executive_cognition",
        "knowledge_update",
        "memory_update",
        "learning_update",
        "adaptive_planning",
    )

    @property
    def deterministic_hash(self) -> int:
        return hash(self.steps)


@dataclass(frozen=True, slots=True)
class ExecutionTrace:
    """Trace of executed steps during a tick (identical to plan in this simple impl)."""

    executed_steps: Tuple[str, ...] = (
        "physiology_update",
        "complication_propagation",
        "executive_cognition",
        "knowledge_update",
        "memory_update",
        "learning_update",
        "adaptive_planning",
    )

    @property
    def deterministic_hash(self) -> int:
        return hash(self.executed_steps)


@dataclass(frozen=True, slots=True)
class MetaSnapshot:
    """Top‑level immutable snapshot produced by MetaManager.tick()."""

    state: Any  # The full world/state object (opaque for this layer)
    consistency_report: SystemConsistencyReport
    invariant_check: DeterministicInvariantCheck
    orchestration_plan: OrchestrationPlan
    execution_trace: ExecutionTrace

    @property
    def deterministic_hash(self) -> int:
        return hash(
            (
                self.state.deterministic_hash if hasattr(self.state, "deterministic_hash") else hash(self.state),
                self.consistency_report.deterministic_hash,
                self.invariant_check.deterministic_hash,
                self.orchestration_plan.deterministic_hash,
                self.execution_trace.deterministic_hash,
            )
        )
