"""Dataclasses for Phase 8.5 deterministic self‑evaluation.
All dataclasses are immutable (frozen, slots) and provide a deterministic_hash
property based on a SHA‑256 digest of their field values.  This guarantees that
identical inputs always produce identical hashes across runs and processes.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict, replace
from typing import Tuple, Any


def _deterministic_hash(obj: Any) -> int:
    """Return a deterministic integer hash for a dataclass instance.

    The object is converted to a dict via ``asdict`` (recursively handling
    nested dataclasses).  The dict is JSON‑serialized with sorted keys and
    compact separators, then hashed using SHA‑256.  The resulting hex digest is
    interpreted as a base‑16 integer.
    """
    # ``asdict`` works only on dataclasses; for non‑dataclasses fallback to ``repr``
    try:
        data = asdict(obj)  # type: ignore[arg-type]
    except Exception:
        data = obj
    json_str = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return int(hashlib.sha256(json_str.encode()).hexdigest(), 16)


# ---------------------------------------------------------------------------
# Core report dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class SystemHealthReport:
    issues: Tuple[str, ...] = ()
    hash_consistency: bool = True

    @property
    def deterministic_hash(self) -> int:
        return _deterministic_hash(self)


@dataclass(frozen=True, slots=True)
class DecisionQualityReport:
    optimality: float = 0.0
    efficiency: float = 0.0
    unnecessary_actions: int = 0
    delayed_actions: int = 0
    confidence_alignment: float = 0.0

    @property
    def deterministic_hash(self) -> int:
        return _deterministic_hash(self)


@dataclass(frozen=True, slots=True)
class PhysiologyCoherenceReport:
    issues: Tuple[str, ...] = ()

    @property
    def deterministic_hash(self) -> int:
        return _deterministic_hash(self)


@dataclass(frozen=True, slots=True)
class KnowledgeConsistencyReport:
    contradictions: Tuple[str, ...] = ()

    @property
    def deterministic_hash(self) -> int:
        return _deterministic_hash(self)


@dataclass(frozen=True, slots=True)
class MemoryAlignmentReport:
    issues: Tuple[str, ...] = ()

    @property
    def deterministic_hash(self) -> int:
        return _deterministic_hash(self)


@dataclass(frozen=True, slots=True)
class LearningEffectivenessReport:
    useless_policies: Tuple[str, ...] = ()
    stale_learning: Tuple[str, ...] = ()
    over_generalization: Tuple[str, ...] = ()

    @property
    def deterministic_hash(self) -> int:
        return _deterministic_hash(self)


@dataclass(frozen=True, slots=True)
class SimulationDriftReport:
    structural_drift: int = 0
    behavioral_drift: int = 0
    physiological_drift: int = 0
    executive_drift: int = 0
    knowledge_drift: int = 0
    memory_drift: int = 0

    @property
    def deterministic_hash(self) -> int:
        return _deterministic_hash(self)


@dataclass(frozen=True, slots=True)
class CorrectionProposal:
    description: str
    action: str

    @property
    def deterministic_hash(self) -> int:
        return _deterministic_hash(self)


@dataclass(frozen=True, slots=True)
class CorrectionSet:
    proposals: Tuple[CorrectionProposal, ...] = field(default_factory=tuple)

    @property
    def deterministic_hash(self) -> int:
        return _deterministic_hash(self)


# ---------------------------------------------------------------------------
# Top‑level EvaluationSnapshot
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class EvaluationSnapshot:
    health_report: SystemHealthReport
    decision_quality_report: DecisionQualityReport
    physiology_coherence_report: PhysiologyCoherenceReport
    knowledge_consistency_report: KnowledgeConsistencyReport
    memory_alignment_report: MemoryAlignmentReport
    learning_effectiveness_report: LearningEffectivenessReport
    simulation_drift_report: SimulationDriftReport
    correction_set: CorrectionSet

    @property
    def deterministic_hash(self) -> int:
        return _deterministic_hash(self)
