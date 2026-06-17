"""Deterministic stabilization dataclasses for Phase 8.6.
All dataclasses are frozen, slots‑based, and provide a deterministic hash based
on a tuple of primitive fields.  Collections are immutable ``tuple`` objects and
are sorted where ordering matters.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Tuple, Any
import hashlib
import json

def _det_hash(obj: Any) -> int:
    """Return a deterministic integer hash for a dataclass instance.

    The object is converted to a dict via ``asdict`` (recursively handling nested
    dataclasses).  The dict is JSON‑serialized with sorted keys and compact
    separators, then hashed with SHA‑256.  The resulting hex digest is interpreted
    as a base‑16 integer, guaranteeing identical hashes across interpreter runs.
    """
    try:
        data = asdict(obj)  # type: ignore[arg-type]
    except Exception:
        data = str(obj)
    json_str = json.dumps(data, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(json_str.encode()).digest()
    return int.from_bytes(digest[:8], "big", signed=True)



# ---------------------------------------------------------------------------
# Core stabilization structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class DriftVector:
    structural_drift: float
    behavioral_drift: float
    physiological_drift: float
    cognitive_drift: float

    @property
    def deterministic_hash(self) -> int:
        return _det_hash(self)


@dataclass(frozen=True, slots=True)
class StabilityViolation:
    description: str
    severity: float

    @property
    def deterministic_hash(self) -> int:
        return _det_hash(self)


@dataclass(frozen=True, slots=True)
class SystemStabilityState:
    stability_score: float
    violations: Tuple[StabilityViolation, ...] = ()

    @property
    def deterministic_hash(self) -> int:
        return _det_hash(self)


@dataclass(frozen=True, slots=True)
class CorrectionAction:
    target_component: str
    action_type: str
    parameters: Tuple[Any, ...] = ()

    @property
    def deterministic_hash(self) -> int:
        return _det_hash(self)


@dataclass(frozen=True, slots=True)
class CorrectionPlan:
    actions: Tuple[CorrectionAction, ...] = ()

    @property
    def deterministic_hash(self) -> int:
        return _det_hash(self)


@dataclass(frozen=True, slots=True)
class RollbackState:
    required: bool
    target_hash: int

    @property
    def deterministic_hash(self) -> int:
        return _det_hash(self)


@dataclass(frozen=True, slots=True)
class ConvergenceReport:
    status: str  # "fixed_point", "oscillation", "divergence"
    details: Tuple[Any, ...] = ()

    @property
    def deterministic_hash(self) -> int:
        return _det_hash(self)


@dataclass(frozen=True, slots=True)
class StabilizationSnapshot:
    drift: DriftVector
    stability: SystemStabilityState
    convergence: ConvergenceReport
    correction_plan: CorrectionPlan
    rollback: RollbackState
    # Include the original deterministic hash for reproducibility check.
    original_hash: int

    @property
    def deterministic_hash(self) -> int:
        return _det_hash(self)
