from dataclasses import dataclass, field
from typing import Dict

@dataclass
class StaffFatigueProfile:
    baseline_latency_ms: int = 500
    fatigue_level: float = 0.0
    cognitive_overload: float = 0.0
    shift_hours_elapsed: float = 0.0

    @property
    def current_latency_multiplier(self) -> float:
        return 1.0 + (self.fatigue_level * 1.5) + (self.cognitive_overload * 2.0)

    @property
    def error_rate(self) -> float:
        return (self.fatigue_level * 0.15) + (self.cognitive_overload * 0.25)

    def to_dict(self) -> dict:
        return {
            "baseline_latency_ms": self.baseline_latency_ms,
            "fatigue_level": round(self.fatigue_level, 6),
            "cognitive_overload": round(self.cognitive_overload, 6),
            "shift_hours_elapsed": round(self.shift_hours_elapsed, 6),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "StaffFatigueProfile":
        return cls(
            baseline_latency_ms=d.get("baseline_latency_ms", 500),
            fatigue_level=d.get("fatigue_level", 0.0),
            cognitive_overload=d.get("cognitive_overload", 0.0),
            shift_hours_elapsed=d.get("shift_hours_elapsed", 0.0),
        )


@dataclass
class StaffSystemState:
    available_nurses: int = 10
    available_physicians: int = 3
    available_surgeons: int = 1
    available_respiratory_therapists: int = 2

    team_fatigue: StaffFatigueProfile = field(default_factory=StaffFatigueProfile)

    def to_dict(self) -> dict:
        return {
            "available_nurses": self.available_nurses,
            "available_physicians": self.available_physicians,
            "available_surgeons": self.available_surgeons,
            "available_respiratory_therapists": self.available_respiratory_therapists,
            "team_fatigue": self.team_fatigue.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "StaffSystemState":
        return cls(
            available_nurses=d.get("available_nurses", 10),
            available_physicians=d.get("available_physicians", 3),
            available_surgeons=d.get("available_surgeons", 1),
            available_respiratory_therapists=d.get("available_respiratory_therapists", 2),
            team_fatigue=StaffFatigueProfile.from_dict(d.get("team_fatigue", {})),
        )
    
    def evolve(self):
        # Linearly accumulate shift fatigue
        self.team_fatigue.shift_hours_elapsed += 0.1 # Every tick is 6 minutes
        if self.team_fatigue.shift_hours_elapsed > 8.0:
            self.team_fatigue.fatigue_level = min(1.0, self.team_fatigue.fatigue_level + 0.02)
            
    def adjust_overload(self, active_critical_patients: int):
        # Calculate ratio of critical patients to staff
        ratio = active_critical_patients / max(1, self.available_nurses + self.available_physicians)
        
        # High ratio -> cognitive overload
        if ratio > 1.0:
            self.team_fatigue.cognitive_overload = min(1.0, (ratio - 1.0) * 0.5)
        else:
            self.team_fatigue.cognitive_overload = max(0.0, self.team_fatigue.cognitive_overload - 0.1)
