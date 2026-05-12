from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class EnvironmentalPressure:
    type: str
    severity: float
    affected_patients: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "severity": round(self.severity, 6),
            "affected_patients": sorted(self.affected_patients),
        }


@dataclass
class OutbreakState:
    active_pressures: Dict[str, EnvironmentalPressure] = field(default_factory=dict)
    icu_contamination_level: float = 0.0

    def to_dict(self) -> dict:
        return {
            "active_pressures": {
                k: v.to_dict() for k, v in sorted(self.active_pressures.items())
            },
            "icu_contamination_level": round(self.icu_contamination_level, 6),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "OutbreakState":
        pressures = {}
        for k, v in d.get("active_pressures", {}).items():
            if isinstance(v, dict):
                pressures[k] = EnvironmentalPressure(
                    type=v.get("type", ""),
                    severity=v.get("severity", 0.0),
                    affected_patients=v.get("affected_patients", []),
                )
            else:
                pressures[k] = v
        return cls(
            active_pressures=pressures,
            icu_contamination_level=d.get("icu_contamination_level", 0.0),
        )
    
    def evolve(self):
        # Naturally decay contamination if no active spreader
        self.icu_contamination_level = max(0.0, self.icu_contamination_level - 0.01)
        
        # Evolve specific outbreaks
        for pressure in self.active_pressures.values():
            if pressure.type == "vap": # Ventilator-associated pneumonia
                pressure.severity = min(1.0, pressure.severity + 0.05)
            elif pressure.type == "mrsa_outbreak":
                pressure.severity = min(1.0, pressure.severity + 0.02)
                self.icu_contamination_level = min(1.0, self.icu_contamination_level + 0.05)
