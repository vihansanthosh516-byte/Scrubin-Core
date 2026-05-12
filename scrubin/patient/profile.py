from dataclasses import dataclass, field

from scrubin.models.types import Vitals


@dataclass
class PatientProfile:
    id: str
    age: int = 50
    weight: float = 75.0
    baseline_vitals: Vitals = field(default_factory=Vitals)
    risk_factors: tuple[str, ...] = ()
    complication_probability: dict[str, float] = field(default_factory=dict)
    recovery_rate: float = 1.0
    deterioration_rate: float = 1.0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "demographics": {"age": self.age, "weight": self.weight},
            "baseline_vitals": self.baseline_vitals.to_dict(),
            "risk_factors": list(self.risk_factors),
            "modifiers": {
                "complication_probability": self.complication_probability,
                "recovery_rate": self.recovery_rate,
                "deterioration_rate": self.deterioration_rate,
            },
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PatientProfile":
        bv = d.get("baseline_vitals", {})
        modifiers = d.get("modifiers", {})
        return cls(
            id=d["id"],
            age=d.get("demographics", {}).get("age", 50),
            weight=d.get("demographics", {}).get("weight", 75.0),
            baseline_vitals=Vitals.from_dict(bv),
            risk_factors=tuple(d.get("risk_factors", [])),
            complication_probability=modifiers.get("complication_probability", {}),
            recovery_rate=modifiers.get("recovery_rate", 1.0),
            deterioration_rate=modifiers.get("deterioration_rate", 1.0),
        )

    def complication_prob_modifier(self, complication_id: str) -> float:
        return self.complication_probability.get(complication_id, 1.0)

    def vital_range_modifiers(self) -> dict[str, tuple[float, float]]:
        adjustments = {}
        if "hypertension" in self.risk_factors:
            adjustments["bp_systolic"] = (100, 160)
            adjustments["bp_diastolic"] = (65, 100)
        if "diabetes" in self.risk_factors:
            adjustments["heart_rate"] = (55, 110)
        if "copd" in self.risk_factors or "smoker" in self.risk_factors:
            adjustments["spo2"] = (90, 98)
        if self.age >= 70:
            if "spo2" not in adjustments:
                adjustments["spo2"] = (92, 98)
            if "heart_rate" not in adjustments:
                adjustments["heart_rate"] = (50, 90)
        return adjustments


STANDARD_PATIENT = PatientProfile(
    id="standard",
    age=50,
    weight=75.0,
    baseline_vitals=Vitals(spo2=97.0, heart_rate=80.0, bp_systolic=115.0, bp_diastolic=75.0, temperature=36.6),
    risk_factors=(),
    recovery_rate=1.0,
    deterioration_rate=1.0,
)

ELDERLY_HIGH_RISK = PatientProfile(
    id="elderly_high_risk",
    age=78,
    weight=65.0,
    baseline_vitals=Vitals(spo2=94.0, heart_rate=88.0, bp_systolic=135.0, bp_diastolic=82.0, temperature=37.2),
    risk_factors=("hypertension", "diabetes"),
    complication_probability={"infection": 1.5, "hypotension": 1.3, "hypoxia": 1.4},
    recovery_rate=0.7,
    deterioration_rate=1.4,
)

YOUNG_HEALTHY = PatientProfile(
    id="young_healthy",
    age=28,
    weight=70.0,
    baseline_vitals=Vitals(spo2=99.0, heart_rate=72.0, bp_systolic=110.0, bp_diastolic=70.0, temperature=36.4),
    risk_factors=(),
    complication_probability={"hemorrhage": 0.8},
    recovery_rate=1.3,
    deterioration_rate=0.7,
)

CHRONIC_COPD = PatientProfile(
    id="chronic_copd",
    age=65,
    weight=60.0,
    baseline_vitals=Vitals(spo2=92.0, heart_rate=90.0, bp_systolic=125.0, bp_diastolic=78.0, temperature=36.8),
    risk_factors=("copd", "smoker"),
    complication_probability={"hypoxia": 2.0, "infection": 1.6, "thrombosis": 1.3},
    recovery_rate=0.6,
    deterioration_rate=1.5,
)

PATIENT_PROFILES: dict[str, PatientProfile] = {
    "standard": STANDARD_PATIENT,
    "elderly_high_risk": ELDERLY_HIGH_RISK,
    "young_healthy": YOUNG_HEALTHY,
    "chronic_copd": CHRONIC_COPD,
}
