from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class VitalThresholds:
    normal_lo: float
    normal_hi: float
    warning_lo: float
    warning_hi: float
    critical_lo: float
    critical_hi: float
    absolute_floor: float = 0.0
    absolute_ceiling: float = 999.0

    def range_tuple(self) -> tuple[float, float]:
        return (self.normal_lo, self.normal_hi)

    def is_critical(self, value: float) -> bool:
        return value <= self.critical_lo or value >= self.critical_hi

    def is_warning(self, value: float) -> bool:
        return value <= self.warning_lo or value >= self.warning_hi


@dataclass(frozen=True)
class SeverityThresholds:
    spo2_severe: float
    spo2_moderate: float
    bp_systolic_severe: float
    bp_systolic_moderate: float
    temperature_severe: float
    temperature_moderate: float
    heart_rate_tachycardia: float
    heart_rate_bradycardia: float


@dataclass(frozen=True)
class EscalationThresholds:
    complication_probability: float
    severity_weights: tuple[float, float, float]


@dataclass
class ClinicalThresholds:
    spo2: VitalThresholds
    heart_rate: VitalThresholds
    bp_systolic: VitalThresholds
    bp_diastolic: VitalThresholds
    temperature: VitalThresholds
    severity: SeverityThresholds
    escalation: EscalationThresholds

    @classmethod
    def defaults(cls) -> "ClinicalThresholds":
        return cls(
            spo2=VitalThresholds(
                normal_lo=94.0, normal_hi=100.0,
                warning_lo=85.0, warning_hi=100.0,
                critical_lo=70.0, critical_hi=100.0,
                absolute_floor=50.0,
            ),
            heart_rate=VitalThresholds(
                normal_lo=60.0, normal_hi=100.0,
                warning_lo=50.0, warning_hi=110.0,
                critical_lo=40.0, critical_hi=180.0,
            ),
            bp_systolic=VitalThresholds(
                normal_lo=90.0, normal_hi=140.0,
                warning_lo=80.0, warning_hi=160.0,
                critical_lo=60.0, critical_hi=200.0,
            ),
            bp_diastolic=VitalThresholds(
                normal_lo=60.0, normal_hi=90.0,
                warning_lo=50.0, warning_hi=100.0,
                critical_lo=40.0, critical_hi=120.0,
            ),
            temperature=VitalThresholds(
                normal_lo=36.1, normal_hi=37.2,
                warning_lo=35.0, warning_hi=38.0,
                critical_lo=34.0, critical_hi=39.0,
            ),
            severity=SeverityThresholds(
                spo2_severe=85.0, spo2_moderate=92.0,
                bp_systolic_severe=70.0, bp_systolic_moderate=90.0,
                temperature_severe=39.0, temperature_moderate=38.0,
                heart_rate_tachycardia=100.0, heart_rate_bradycardia=60.0,
            ),
            escalation=EscalationThresholds(
                complication_probability=0.15,
                severity_weights=(0.5, 0.35, 0.15),
            ),
        )

    def apply_patient_modifiers(self, modifiers: dict[str, tuple[float, float]]) -> "ClinicalThresholds":
        d = {
            "spo2": self.spo2,
            "heart_rate": self.heart_rate,
            "bp_systolic": self.bp_systolic,
            "bp_diastolic": self.bp_diastolic,
            "temperature": self.temperature,
        }
        for key, (lo, hi) in modifiers.items():
            if key in d:
                old = d[key]
                span = hi - lo
                warn_lo_pct = (old.warning_lo - old.normal_lo) / max(old.normal_hi - old.normal_lo, 1)
                warn_hi_pct = (old.normal_hi - old.warning_hi) / max(old.normal_hi - old.normal_lo, 1)
                crit_lo_pct = (old.critical_lo - old.normal_lo) / max(old.normal_hi - old.normal_lo, 1)
                crit_hi_pct = (old.critical_hi - old.normal_hi) / max(old.normal_hi - old.normal_lo, 1)
                d[key] = VitalThresholds(
                    normal_lo=lo, normal_hi=hi,
                    warning_lo=lo + warn_lo_pct * span,
                    warning_hi=hi - warn_hi_pct * span,
                    critical_lo=lo + crit_lo_pct * span,
                    critical_hi=hi - crit_hi_pct * span,
                    absolute_floor=old.absolute_floor,
                    absolute_ceiling=old.absolute_ceiling,
                )
        return ClinicalThresholds(
            spo2=d["spo2"],
            heart_rate=d["heart_rate"],
            bp_systolic=d["bp_systolic"],
            bp_diastolic=d["bp_diastolic"],
            temperature=d["temperature"],
            severity=self.severity,
            escalation=self.escalation,
        )

    def vital_ranges(self) -> dict[str, tuple[float, float]]:
        return {
            "spo2": self.spo2.range_tuple(),
            "heart_rate": self.heart_rate.range_tuple(),
            "bp_systolic": self.bp_systolic.range_tuple(),
            "bp_diastolic": self.bp_diastolic.range_tuple(),
            "temperature": self.temperature.range_tuple(),
        }

    def determine_severity(self, complication_category: str, vitals: dict) -> str:
        if complication_category == "respiratory":
            spo2 = vitals.get("spo2", 97)
            if spo2 < self.severity.spo2_severe:
                return "severe"
            elif spo2 < self.severity.spo2_moderate:
                return "moderate"
            return "mild"
        elif complication_category == "cardiovascular":
            bp = vitals.get("bp_systolic", 115)
            if bp < self.severity.bp_systolic_severe:
                return "severe"
            elif bp < self.severity.bp_systolic_moderate:
                return "moderate"
            return "mild"
        elif complication_category == "infectious":
            temp = vitals.get("temperature", 36.6)
            if temp > self.severity.temperature_severe:
                return "severe"
            elif temp > self.severity.temperature_moderate:
                return "moderate"
            return "mild"
        elif complication_category == "hematologic":
            spo2 = vitals.get("spo2", 97)
            if spo2 < self.severity.spo2_severe:
                return "severe"
            elif spo2 < self.severity.spo2_moderate:
                return "moderate"
            return "mild"
        return "moderate"
