from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ActionIntent:
    id: str
    type: str
    name: str
    target: str | None
    priority: float
    confidence: float
    source: str
    reasoning: str
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "target": self.target,
            "priority": self.priority,
            "confidence": self.confidence,
            "source": self.source,
            "reasoning": self.reasoning,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ActionIntent":
        return cls(
            id=d["id"],
            type=d["type"],
            name=d["name"],
            target=d.get("target"),
            priority=d.get("priority", 0.0),
            confidence=d.get("confidence", 0.0),
            source=d.get("source", "engine"),
            reasoning=d.get("reasoning", ""),
            metadata=d.get("metadata", {}),
        )


@dataclass(frozen=True)
class ValidationResult:
    approved: bool
    confidence: float
    delta: float

    def to_dict(self) -> dict:
        return {
            "approved": self.approved,
            "confidence": self.confidence,
            "delta": self.delta,
        }
