"""Deterministic scenario dataclasses for Phase 8.4.
All dataclasses are frozen, use slots, and provide deterministic hashes.
"""

from __future__ import annotations

from dataclasses import dataclass, replace, field
from scrubin.learning.models import _det_hash
from typing import Tuple, Any

# ---------------------------------------------------------------------------
# Core scenario model used by workflow engine
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ProcedureScenario:
    id: str
    display_name: str
    specialty: str
    difficulty: str
    description: str
    patient: Any
    operative_context: Any
    resources: Any
    workflow: Tuple[Any, ...]
    baseline_physiology: Any = field(default_factory=dict)
    team_roles: Tuple[Any, ...] = ()
    anatomy_structures: Tuple[Any, ...] = ()
    complications: Tuple[Any, ...] = ()
    success_conditions: Tuple[Any, ...] = ()
    failure_conditions: Tuple[Any, ...] = ()
    teaching_objectives: Tuple[Any, ...] = ()
    estimated_duration_minutes: int = 0
    educational: Any = None

    @property
    def deterministic_hash(self) -> int:
        return _det_hash(self)

# ---------------------------------------------------------------------------
# Supporting placeholder structures for workflow tests
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Complication:
    id: str
    severity: float

    @property
    def deterministic_hash(self) -> int:
        return _det_hash(self)

@dataclass(frozen=True, slots=True)
class PatientInfo:
    age: int
    sex: str
    bmi: float
    diagnosis: str
    comorbidities: Tuple[Any, ...]
    allergies: Tuple[Any, ...]
    baseline_vitals: Any

    @property
    def deterministic_hash(self) -> int:
        return _det_hash(self)

@dataclass(frozen=True, slots=True)
class OperativeContext:
    or_setup: str
    positioning: str
    anatomy_variant: str
    pathology_severity: str

    @property
    def deterministic_hash(self) -> int:
        return _det_hash(self)

@dataclass(frozen=True, slots=True)
class Resources:
    instruments: Tuple[str, ...] = ("scalpel", "retractor", "forceps")
    staff: Tuple[str, ...] = ()
    medications: Tuple[str, ...] = ()
    implants: Tuple[str, ...] = ()
    equipment: Tuple[str, ...] = ()

    @property
    def deterministic_hash(self) -> int:
        return _det_hash(self)

@dataclass(frozen=True, slots=True)
class Step:
    id: str
    description: str = ""
    duration: float = 0.0
    prerequisite_steps: Tuple[str, ...] = ()
    required_instruments: Tuple[str, ...] = ()
    required_medications: Tuple[str, ...] = ()
    required_implants: Tuple[str, ...] = ()
    required_equipment: Tuple[str, ...] = ()
    required_roles: Tuple[str, ...] = ()

    @property
    def deterministic_hash(self) -> int:
        return _det_hash(self)

@dataclass(frozen=True, slots=True)
class TeamRole:
    id: str
    role_type: str

    @property
    def deterministic_hash(self) -> int:
        return _det_hash(self)

# ---------------------------------------------------------------------------
# Scenario generation structures (unchanged from previous implementation)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ScenarioSeed:
    procedure_id: str
    anatomy_complexity: int
    physiology_hash: int
    environment_hash: int

    @property
    def deterministic_hash(self) -> int:
        return _det_hash(self)

@dataclass(frozen=True, slots=True)
class StressVector:
    name: str
    magnitude: float

    @property
    def deterministic_hash(self) -> int:
        return _det_hash(self)

@dataclass(frozen=True, slots=True)
class AdversarialCondition:
    description: str
    severity: float

    @property
    def deterministic_hash(self) -> int:
        return _det_hash(self)

@dataclass(frozen=True, slots=True)
class FailureMode:
    component: str
    failure_type: str

    @property
    def deterministic_hash(self) -> int:
        return _det_hash(self)

@dataclass(frozen=True, slots=True)
class ScenarioProfile:
    seed: ScenarioSeed
    stress_vectors: Tuple[StressVector, ...] = ()
    adversarial_conditions: Tuple[AdversarialCondition, ...] = ()
    failure_modes: Tuple[FailureMode, ...] = ()

    @property
    def deterministic_hash(self) -> int:
        return hash((self.seed.deterministic_hash,
                     tuple(s.deterministic_hash for s in self.stress_vectors),
                     tuple(a.deterministic_hash for a in self.adversarial_conditions),
                     tuple(f.deterministic_hash for f in self.failure_modes)))

@dataclass(frozen=True, slots=True)
class ScenarioSnapshot:
    world: Any
    profile: ScenarioProfile

    @property
    def deterministic_hash(self) -> int:
        return hash((self.world.deterministic_hash if hasattr(self.world, "deterministic_hash") else hash(self.world), self.profile.deterministic_hash))
