from dataclasses import dataclass, field, replace
from typing import Literal, Optional


ComplicationSeverity = Literal["mild", "moderate", "severe"]
RiskLevel = Literal["low", "medium", "high"]
SimulationStatus = Literal["initialized", "running", "completed", "replayed"]


@dataclass(frozen=True)
class Vitals:
    spo2: float = 97.0
    heart_rate: float = 80.0
    bp_systolic: float = 115.0
    bp_diastolic: float = 75.0
    temperature: float = 36.6

    def to_dict(self) -> dict:
        return {
            "spo2": self.spo2,
            "heart_rate": self.heart_rate,
            "bp_systolic": self.bp_systolic,
            "bp_diastolic": self.bp_diastolic,
            "temperature": self.temperature,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Vitals":
        return cls(
            spo2=d.get("spo2", 97.0),
            heart_rate=d.get("heart_rate", 80.0),
            bp_systolic=d.get("bp_systolic", 115.0),
            bp_diastolic=d.get("bp_diastolic", 75.0),
            temperature=d.get("temperature", 36.6),
        )


@dataclass(frozen=True)
class VitalDelta:
    spo2: float = 0.0
    heart_rate: float = 0.0
    bp_systolic: float = 0.0
    bp_diastolic: float = 0.0
    temperature: float = 0.0

    def to_dict(self) -> dict:
        return {
            "spo2": self.spo2,
            "heart_rate": self.heart_rate,
            "bp_systolic": self.bp_systolic,
            "bp_diastolic": self.bp_diastolic,
            "temperature": self.temperature,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "VitalDelta":
        return cls(
            spo2=d.get("spo2", 0.0),
            heart_rate=d.get("heart_rate", 0.0),
            bp_systolic=d.get("bp_systolic", 0.0),
            bp_diastolic=d.get("bp_diastolic", 0.0),
            temperature=d.get("temperature", 0.0),
        )

    def __add__(self, other: "VitalDelta") -> "VitalDelta":
        return VitalDelta(
            spo2=self.spo2 + other.spo2,
            heart_rate=self.heart_rate + other.heart_rate,
            bp_systolic=self.bp_systolic + other.bp_systolic,
            bp_diastolic=self.bp_diastolic + other.bp_diastolic,
            temperature=self.temperature + other.temperature,
        )

    def __mul__(self, factor: float) -> "VitalDelta":
        return VitalDelta(
            spo2=self.spo2 * factor,
            heart_rate=self.heart_rate * factor,
            bp_systolic=self.bp_systolic * factor,
            bp_diastolic=self.bp_diastolic * factor,
            temperature=self.temperature * factor,
        )


@dataclass(frozen=True)
class ComplicationState:
    id: str
    severity: ComplicationSeverity
    onset_tick: int
    lifecycle: str = "active"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "severity": self.severity,
            "onset_tick": self.onset_tick,
            "lifecycle": self.lifecycle,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ComplicationState":
        return cls(
            id=d["id"],
            severity=d.get("severity", "moderate"),
            onset_tick=d.get("onset_tick", 0),
            lifecycle=d.get("lifecycle", "active"),
        )

    def with_severity(self, severity: ComplicationSeverity) -> "ComplicationState":
        return replace(self, severity=severity)

    def with_lifecycle(self, lifecycle: str) -> "ComplicationState":
        return replace(self, lifecycle=lifecycle)


@dataclass
class SimulationState:
    tick: int = 0
    vitals: Vitals = field(default_factory=Vitals)
    complications: list[ComplicationState] = field(default_factory=list)
    procedures: list[str] = field(default_factory=list)
    status: str = "initialized"
    seed: int = 0
    patient_profile: str = "standard"
    mode: str = "autonomous"

    def to_dict(self) -> dict:
        return {
            "tick": self.tick,
            "vitals": self.vitals.to_dict(),
            "complications": [c.to_dict() for c in self.complications],
            "procedures": list(self.procedures),
            "status": self.status,
            "seed": self.seed,
            "patient_profile": self.patient_profile,
            "mode": self.mode,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SimulationState":
        vitals_data = d.get("vitals", {})
        vitals = Vitals.from_dict(vitals_data) if isinstance(vitals_data, dict) else Vitals()
        return cls(
            tick=d.get("tick", 0),
            vitals=vitals,
            complications=[
                ComplicationState.from_dict(c) if isinstance(c, dict) else c
                for c in d.get("complications", [])
            ],
            procedures=d.get("procedures", []),
            status=d.get("status", "initialized"),
            seed=d.get("seed", 0),
            patient_profile=d.get("patient_profile", "standard"),
            mode=d.get("mode", "autonomous"),
        )

    def with_vitals(self, vitals: Vitals) -> "SimulationState":
        self.vitals = vitals
        return self

    def with_tick(self, tick: int) -> "SimulationState":
        self.tick = tick
        return self

    def advance(self) -> int:
        self.tick += 1
        return self.tick

    def add_complication(self, comp: ComplicationState) -> None:
        self.complications = [c for c in self.complications if c.id != comp.id or c.onset_tick != comp.onset_tick]
        self.complications.append(comp)

    def add_procedure(self, procedure_name: str) -> None:
        self.procedures.append(procedure_name)

    def update_complication(self, comp_id: str, severity: ComplicationSeverity = None, lifecycle: str = None) -> None:
        updated = []
        for c in self.complications:
            if c.id == comp_id:
                new_sev = severity if severity is not None else c.severity
                new_lc = lifecycle if lifecycle is not None else c.lifecycle
                c = c.with_severity(new_sev).with_lifecycle(new_lc)
            updated.append(c)
        self.complications = updated


@dataclass
class DecisionOption:
    id: str
    label: str
    archetype: str
    expected_impact: VitalDelta
    risk_level: RiskLevel
    target_complication: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "archetype": self.archetype,
            "expected_impact": self.expected_impact.to_dict(),
            "risk_level": self.risk_level,
            "target_complication": self.target_complication,
        }
