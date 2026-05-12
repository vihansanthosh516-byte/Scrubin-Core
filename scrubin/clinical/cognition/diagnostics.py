from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class HiddenCondition:
    id: str
    severity: str
    onset_tick: int
    observability: float
    progression_rate: float

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "severity": self.severity,
            "onset_tick": self.onset_tick,
            "observability": round(self.observability, 6),
            "progression_rate": round(self.progression_rate, 6),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "HiddenCondition":
        return cls(
            id=d["id"],
            severity=d["severity"],
            onset_tick=d["onset_tick"],
            observability=d.get("observability", 0.0),
            progression_rate=d.get("progression_rate", 0.0),
        )

@dataclass
class ClinicalFinding:
    type: str
    confidence: float
    source: str
    supporting_vitals: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "confidence": round(self.confidence, 6),
            "source": self.source,
            "supporting_vitals": dict(sorted(self.supporting_vitals.items())),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ClinicalFinding":
        return cls(
            type=d["type"],
            confidence=d.get("confidence", 0.0),
            source=d.get("source", ""),
            supporting_vitals=d.get("supporting_vitals", {}),
        )
