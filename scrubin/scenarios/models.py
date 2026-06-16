"""Immutable data model for deterministic surgical procedure scenarios.

All fields are frozen ``dataclass`` instances to guarantee immutability and
hash‑ability.  Optional educational metadata is stored in ``educational`` and
is deliberately excluded from deterministic hashing.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from dataclasses import asdict
from typing import List, Dict, Tuple, Optional
from scrubin.anatomy.models import AnatomicalStructure

# ---------------------------------------------------------------------------
# Sub‑components
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class PatientInfo:
    age: int
    sex: str  # "M"/"F"
    bmi: float
    diagnosis: str
    comorbidities: Tuple[str, ...] = field(default_factory=tuple)
    allergies: Tuple[str, ...] = field(default_factory=tuple)
    baseline_vitals: Dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class OperativeContext:
    or_setup: str
    positioning: str
    anatomy_variant: str
    pathology_severity: str


@dataclass(frozen=True, slots=True)
class Resources:
    instruments: Tuple[str, ...] = field(default_factory=tuple)
    staff: Tuple[str, ...] = field(default_factory=tuple)
    medications: Tuple[str, ...] = field(default_factory=tuple)
    implants: Tuple[str, ...] = field(default_factory=tuple)
    equipment: Tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class Step:
    """A single deterministic workflow step.

    * ``id`` – Unique identifier within the scenario (e.g., ``establish_access``).
    """
    id: str
    description: str = ""
    # Prerequisite step IDs that must be completed before this step can run.
    prerequisite_steps: Tuple[str, ...] = field(default_factory=tuple)
    # Resource requirements for deterministic execution.
    required_instruments: Tuple[str, ...] = field(default_factory=tuple)
    required_medications: Tuple[str, ...] = field(default_factory=tuple)
    required_implants: Tuple[str, ...] = field(default_factory=tuple)
    required_equipment: Tuple[str, ...] = field(default_factory=tuple)
    # Deterministic role requirements for the step.
    required_roles: Tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class Complication:
    """Deterministic complication definition.

    * ``id`` – Unique identifier.
    * ``trigger`` – Description of condition that triggers the complication.
    * ``effects`` – Deterministic physiological effects (free‑form string).
    * ``resolution`` – Condition under which the complication resolves.
    """
    id: str
    trigger: str
    effects: str
    resolution: str
# ---------------------------------------------------------------------------
# Team role definition – immutable
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class TeamRole:
    """Static role definition for deterministic OR team.

    * ``id`` – Unique deterministic identifier for the role instance.
    * ``role_type`` – Role type (e.g., ``PrimarySurgeon``).
    """
    id: str
    role_type: str
    deterministic_id: str = field(init=False)

    def __post_init__(self) -> None:
        # deterministic identifier based on static role id
        object.__setattr__(self, "deterministic_id", hashlib.sha256(self.id.encode()).hexdigest())




# ---------------------------------------------------------------------------
# Main scenario model
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ProcedureScenario:
    # Core identification
    id: str
    display_name: str
    specialty: str
    difficulty: str
    description: str

    # Patient and operative context
    patient: PatientInfo
    operative_context: OperativeContext
    resources: Resources

    # Workflow – ordered immutable step list
    workflow: Tuple[Step, ...]
    # Complications – optional list
    complications: Tuple[Complication, ...] = field(default_factory=tuple)

    # Success / failure conditions (free‑form strings for now)
    success_conditions: Tuple[str, ...] = field(default_factory=tuple)
    failure_conditions: Tuple[str, ...] = field(default_factory=tuple)

    # Teaching / educational metadata – excluded from deterministic hash
    teaching_objectives: Tuple[str, ...] = field(default_factory=tuple)
    estimated_duration_minutes: int = 0
    educational: Dict[str, str] = field(default_factory=dict)  # UI‑only fields

    # -------------------- New deterministic fields --------------------
    # Baseline physiology values – affect initial state and deterministic hash.
    baseline_physiology: Dict[str, float] = field(default_factory=dict)
    # Optional per‑step physiology modifiers (step_id -> dict of changes)
    step_physiology_modifiers: Dict[str, Dict[str, float]] = field(default_factory=dict)
    # Complication parameters – coefficients for deterministic impact.
    complication_parameters: Dict[str, Dict[str, float]] = field(default_factory=dict)
    # Progression and recovery coefficients (generic scalar values).
    progression_coefficients: Dict[str, float] = field(default_factory=dict)
    recovery_coefficients: Dict[str, float] = field(default_factory=dict)
    # Deterministic team role definitions – static role set for the scenario.
    team_roles: Tuple[TeamRole, ...] = field(default_factory=tuple)
    # Deterministic anatomy structures – static definitions for the scenario.
    anatomy_structures: Tuple[AnatomicalStructure, ...] = field(default_factory=tuple)

    # --------------------------------------------------------------------
    # Deterministic hash – excludes UI‑only ``educational`` field.
    # --------------------------------------------------------------------
    def deterministic_hash(self) -> str:
        """Return a SHA‑256 hash that uniquely identifies the scenario.

        The hash is computed from a canonical JSON representation containing only
        the fields that affect simulation replay.  UI‑only metadata is omitted.
        """
        # Build a plain Python structure respecting ordering.
        data = {
            "id": self.id,
            "display_name": self.display_name,
            "specialty": self.specialty,
            "difficulty": self.difficulty,
            "description": self.description,
            "patient": {
                "age": self.patient.age,
                "sex": self.patient.sex,
                "bmi": self.patient.bmi,
                "diagnosis": self.patient.diagnosis,
                "comorbidities": list(self.patient.comorbidities),
                "allergies": list(self.patient.allergies),
                "baseline_vitals": self.patient.baseline_vitals,
            },
            "operative_context": {
                "or_setup": self.operative_context.or_setup,
                "positioning": self.operative_context.positioning,
                "anatomy_variant": self.operative_context.anatomy_variant,
                "pathology_severity": self.operative_context.pathology_severity,
            },
            "resources": {
                "instruments": list(self.resources.instruments),
                "staff": list(self.resources.staff),
                "medications": list(self.resources.medications),
                "implants": list(self.resources.implants),
                "equipment": list(self.resources.equipment),
            },
            "workflow": [step.id for step in self.workflow],
            "complications": [comp.id for comp in self.complications],
            "success_conditions": list(self.success_conditions),
            "failure_conditions": list(self.failure_conditions),
            "baseline_physiology": self.baseline_physiology,
            "step_physiology_modifiers": self.step_physiology_modifiers,
            "complication_parameters": self.complication_parameters,
            "progression_coefficients": self.progression_coefficients,
            "recovery_coefficients": self.recovery_coefficients,
            "teaching_objectives": list(self.teaching_objectives),
            "estimated_duration_minutes": self.estimated_duration_minutes,
            "team_roles": [{"id": r.id, "role_type": r.role_type} for r in sorted(self.team_roles, key=lambda x: x.id)],
            "anatomy_structures": [
                {k: v for k, v in asdict(s).items() if k != "deterministic_id"}
                for s in sorted(self.anatomy_structures, key=lambda x: x.id)
            ],
        }
        # Canonical JSON (sorted keys, no whitespace) ensures determinism.
        json_str = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(json_str.encode()).hexdigest()
