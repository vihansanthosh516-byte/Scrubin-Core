"""Deterministic immutable models for Phase 8.7 Global Orchestration.
All models are frozen dataclasses with ``slots=True`` and expose a
``deterministic_hash`` property computed via a SHA‑256 digest of their field
values.  Collections are stored as immutable ``tuple`` objects and sorted where
ordering matters to guarantee replay safety.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict, replace
from typing import Any, Tuple, Mapping


def _det_hash(obj: Any) -> int:
    """Return a deterministic integer hash for a dataclass instance.

    The object is converted to a dict via ``asdict`` (recursively handling
    nested dataclasses).  The dict is serialized to JSON with sorted keys and
    compact separators, then hashed using SHA‑256.  The resulting hex digest is
    interpreted as an integer.
    """
    try:
        data = asdict(obj)  # type: ignore[arg-type]
    except Exception:
        # Fallback for non‑dataclass objects – use ``repr``
        data = str(obj)
    json_str = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return int(hashlib.sha256(json_str.encode()).hexdigest(), 16)


# ---------------------------------------------------------------------------
# Core aggregation snapshot – gathers all subsystem snapshots.
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class CrossLayerSnapshot:
    learning_snapshot: Any = None
    adaptive_snapshot: Any = None
    meta_snapshot: Any = None
    simulation_snapshot: Any = None
    scenario_snapshot: Any = None
    evaluation_snapshot: Any = None
    stabilization_snapshot: Any = None
    combined_hash: int = 0

    @property
    def deterministic_hash(self) -> int:
        # If combined_hash already populated, expose it; otherwise compute.
        return self.combined_hash or _det_hash(self)


# ---------------------------------------------------------------------------
# Execution models
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ExecutionStep:
    name: str
    snapshot: Any
    deterministic_hash: int = field(init=False)

    def __post_init__(self):
        # Compute deterministic hash based on name and snapshot hash.
        object.__setattr__(self, "deterministic_hash", _det_hash((self.name, getattr(self.snapshot, "deterministic_hash", 0))))


@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    steps: Tuple[ExecutionStep, ...] = field(default_factory=tuple)

    @property
    def deterministic_hash(self) -> int:
        # Aggregate step hashes in fixed order.
        return _det_hash(tuple(step.deterministic_hash for step in self.steps))


@dataclass(frozen=True, slots=True)
class ExecutionTrace:
    step_names: Tuple[str, ...] = field(default_factory=tuple)

    @property
    def deterministic_hash(self) -> int:
        return _det_hash(self.step_names)


# ---------------------------------------------------------------------------
# Global tick / state representations (lightweight placeholders)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class GlobalTick:
    tick: int

    @property
    def deterministic_hash(self) -> int:
        return _det_hash(self.tick)


@dataclass(frozen=True, slots=True)
class GlobalState:
    # Arbitrary state container – here we only store the tick and a hash.
    tick: int
    state_hash: int = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, "state_hash", _det_hash(self.tick))

    @property
    def deterministic_hash(self) -> int:
        return self.state_hash


# ---------------------------------------------------------------------------
# Integration and verification reports
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class IntegrationReport:
    issues: Tuple[str, ...] = ()
    hash_consistency: bool = True

    @property
    def deterministic_hash(self) -> int:
        return _det_hash(self)


@dataclass(frozen=True, slots=True)
class ReplayVerification:
    issues: Tuple[str, ...] = ()
    verification_passed: bool = True

    @property
    def deterministic_hash(self) -> int:
        return _det_hash(self)


# ---------------------------------------------------------------------------
# Top‑level orchestration snapshot
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class OrchestrationSnapshot:
    cross_layer: CrossLayerSnapshot
    execution_plan: ExecutionPlan
    execution_trace: ExecutionTrace
    integration_report: IntegrationReport
    replay_verification: ReplayVerification

    @property
    def deterministic_hash(self) -> int:
        # Combine deterministic hashes of all components.
        return _det_hash(
            (
                self.cross_layer.deterministic_hash,
                self.execution_plan.deterministic_hash,
                self.execution_trace.deterministic_hash,
                self.integration_report.deterministic_hash,
                self.replay_verification.deterministic_hash,
            )
        )
