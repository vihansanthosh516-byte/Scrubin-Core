from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class OptionDTO:
    id: str
    label: str
    description: str
    risk: str
    expected_outcome: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "risk": self.risk,
            "expected_outcome": self.expected_outcome,
        }


@dataclass(frozen=True)
class EventDTO:
    sequence: int
    tick: int
    event_type: str
    origin: str
    source: str
    intent_id: str
    payload: dict

    def to_dict(self) -> dict:
        return {
            "sequence": self.sequence,
            "tick": self.tick,
            "event_type": self.event_type,
            "origin": self.origin,
            "source": self.source,
            "intent_id": self.intent_id,
            "payload": self.payload,
        }


@dataclass(frozen=True)
class VitalsDTO:
    spo2: float
    heart_rate: float
    bp_systolic: float
    bp_diastolic: float
    temperature: float

    def to_dict(self) -> dict:
        return {
            "spo2": self.spo2,
            "heart_rate": self.heart_rate,
            "bp_systolic": self.bp_systolic,
            "bp_diastolic": self.bp_diastolic,
            "temperature": self.temperature,
        }


@dataclass(frozen=True)
class ComplicationDTO:
    id: str
    severity: str
    onset_tick: int

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "severity": self.severity,
            "onset_tick": self.onset_tick,
        }


@dataclass(frozen=True)
class PatientProfileDTO:
    id: str
    age: int
    weight: float
    risk_factors: tuple[str, ...]
    baseline_vitals: dict

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "age": self.age,
            "weight": self.weight,
            "risk_factors": list(self.risk_factors),
            "baseline_vitals": self.baseline_vitals,
        }


@dataclass
class StateSnapshotDTO:
    tick: int
    vitals: Optional[dict]
    active_complication: Optional[dict]
    last_procedure: Optional[dict]
    last_decision: Optional[dict]
    last_validation: Optional[dict]
    last_execution: Optional[dict]
    patient_profile: str
    mode: str
    options: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "tick": self.tick,
            "vitals": self.vitals,
            "active_complication": self.active_complication,
            "last_procedure": self.last_procedure,
            "last_decision": self.last_decision,
            "last_validation": self.last_validation,
            "last_execution": self.last_execution,
            "patient_profile": self.patient_profile,
            "mode": self.mode,
            "options": self.options,
        }


def map_option_to_dto(option) -> OptionDTO:
    impact = option.expected_impact.to_dict() if hasattr(option.expected_impact, "to_dict") else {}
    nonzero = {k: v for k, v in impact.items() if v != 0.0}
    parts = [f"{k} {'+' if v > 0 else ''}{v}" for k, v in nonzero.items()]
    description = f"Target: {option.target_complication}" if option.target_complication else "General action"
    expected_outcome = ", ".join(parts) if parts else "No vital change expected"

    return OptionDTO(
        id=option.id,
        label=option.label,
        description=description,
        risk=option.risk_level,
        expected_outcome=expected_outcome,
    )


def map_logged_event_to_dto(event, *, origin: str = "engine", source: str = "", intent_id: str = "") -> EventDTO:
    payload = dict(event.payload) if isinstance(event.payload, dict) else {}
    return EventDTO(
        sequence=event.id,
        tick=event.tick,
        event_type=event.type,
        origin=origin,
        source=source,
        intent_id=intent_id,
        payload=payload,
    )


def map_patient_profile_to_dto(profile) -> PatientProfileDTO:
    bv = profile.baseline_vitals.to_dict() if hasattr(profile.baseline_vitals, "to_dict") else {}
    return PatientProfileDTO(
        id=profile.id,
        age=profile.age,
        weight=profile.weight,
        risk_factors=profile.risk_factors,
        baseline_vitals=bv,
    )
