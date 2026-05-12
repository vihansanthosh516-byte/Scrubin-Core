from dataclasses import dataclass, field
from typing import Optional

from scrubin.models.types import ComplicationSeverity, VitalDelta, Vitals


@dataclass(frozen=True)
class SeverityProfile:
    mild: VitalDelta = field(default_factory=VitalDelta)
    moderate: VitalDelta = field(default_factory=VitalDelta)
    severe: VitalDelta = field(default_factory=VitalDelta)

    def for_severity(self, severity: ComplicationSeverity) -> VitalDelta:
        return getattr(self, severity, self.moderate)

    def to_dict(self) -> dict:
        return {
            "mild": self.mild.to_dict(),
            "moderate": self.moderate.to_dict(),
            "severe": self.severe.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SeverityProfile":
        return cls(
            mild=VitalDelta.from_dict(d.get("mild", {})),
            moderate=VitalDelta.from_dict(d.get("moderate", {})),
            severe=VitalDelta.from_dict(d.get("severe", {})),
        )


@dataclass(frozen=True)
class EscalationRule:
    next: Optional[ComplicationSeverity] = None
    probability: float = 0.0

    def to_dict(self) -> dict:
        return {
            "next": self.next,
            "probability": self.probability,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "EscalationRule":
        return cls(
            next=d.get("next"),
            probability=d.get("probability", 0.0),
        )


@dataclass(frozen=True)
class ResolutionRule:
    base_ticks: int = 5
    required_actions: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "base_ticks": self.base_ticks,
            "required_actions": list(self.required_actions),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ResolutionRule":
        return cls(
            base_ticks=d.get("base_ticks", 5),
            required_actions=tuple(d.get("required_actions", [])),
        )


@dataclass(frozen=True)
class ComplicationDefinition:
    id: str
    category: str
    severity_profiles: SeverityProfile = field(default_factory=SeverityProfile)
    escalation: EscalationRule = field(default_factory=EscalationRule)
    resolution: ResolutionRule = field(default_factory=ResolutionRule)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "category": self.category,
            "severity_profiles": self.severity_profiles.to_dict(),
            "escalation": self.escalation.to_dict(),
            "resolution": self.resolution.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ComplicationDefinition":
        return cls(
            id=d["id"],
            category=d.get("category", "general"),
            severity_profiles=SeverityProfile.from_dict(d.get("severity_profiles", {})),
            escalation=EscalationRule.from_dict(d.get("escalation", {})),
            resolution=ResolutionRule.from_dict(d.get("resolution", {})),
        )
