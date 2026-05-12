from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class VitalsUpdatePayload:
    tick: int
    vitals: dict[str, float]

    def to_dict(self) -> dict:
        return {"tick": self.tick, "vitals": dict(self.vitals)}

    @classmethod
    def from_dict(cls, d: dict) -> "VitalsUpdatePayload":
        return cls(tick=d.get("tick", 0), vitals=d.get("vitals", {}))


@dataclass(frozen=True)
class ProcedurePayload:
    tick: int
    procedure: str
    target: str = ""

    def to_dict(self) -> dict:
        return {"tick": self.tick, "procedure": self.procedure, "target": self.target}

    @classmethod
    def from_dict(cls, d: dict) -> "ProcedurePayload":
        return cls(tick=d.get("tick", 0), procedure=d.get("procedure", ""), target=d.get("target", ""))


@dataclass(frozen=True)
class ComplicationPayload:
    tick: int
    complication: str
    severity: str = "moderate"

    def to_dict(self) -> dict:
        return {"tick": self.tick, "complication": self.complication, "severity": self.severity}

    @classmethod
    def from_dict(cls, d: dict) -> "ComplicationPayload":
        return cls(tick=d.get("tick", 0), complication=d.get("complication", ""), severity=d.get("severity", "moderate"))


@dataclass(frozen=True)
class ComplicationSignalPayload:
    tick: int
    complication: str
    severity: str = "moderate"
    vitals_snapshot: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"tick": self.tick, "complication": self.complication, "severity": self.severity, "vitals_snapshot": dict(self.vitals_snapshot)}

    @classmethod
    def from_dict(cls, d: dict) -> "ComplicationSignalPayload":
        return cls(tick=d.get("tick", 0), complication=d.get("complication", ""), severity=d.get("severity", "moderate"), vitals_snapshot=d.get("vitals_snapshot", {}))


@dataclass(frozen=True)
class ComplicationEscalationPayload:
    tick: int
    complication: str
    severity: str = "moderate"
    onset_tick: int = 0

    def to_dict(self) -> dict:
        return {"tick": self.tick, "complication": self.complication, "severity": self.severity, "onset_tick": self.onset_tick}

    @classmethod
    def from_dict(cls, d: dict) -> "ComplicationEscalationPayload":
        return cls(tick=d.get("tick", 0), complication=d.get("complication", ""), severity=d.get("severity", "moderate"), onset_tick=d.get("onset_tick", 0))


@dataclass(frozen=True)
class RecoveryPayload:
    tick: int
    target: str
    status: str = "monitoring"

    def to_dict(self) -> dict:
        return {"tick": self.tick, "target": self.target, "status": self.status}

    @classmethod
    def from_dict(cls, d: dict) -> "RecoveryPayload":
        return cls(tick=d.get("tick", 0), target=d.get("target", ""), status=d.get("status", "monitoring"))


@dataclass(frozen=True)
class DecisionExecutionPayload:
    executed: bool
    action: str
    tick: int
    source: str = ""
    intent_id: str = ""
    confidence: float = 0.0
    target: str = ""
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "executed": self.executed,
            "action": self.action,
            "tick": self.tick,
            "source": self.source,
            "intent_id": self.intent_id,
            "confidence": self.confidence,
            "target": self.target,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "DecisionExecutionPayload":
        return cls(
            executed=d.get("executed", False),
            action=d.get("action", ""),
            tick=d.get("tick", 0),
            source=d.get("source", ""),
            intent_id=d.get("intent_id", ""),
            confidence=d.get("confidence", 0.0),
            target=d.get("target", ""),
            reason=d.get("reason", ""),
        )


_PAYLOAD_REGISTRY: dict[str, type] = {
    "vitals_update": VitalsUpdatePayload,
    "procedure": ProcedurePayload,
    "complication": ComplicationPayload,
    "complication_signal": ComplicationSignalPayload,
    "complication_escalation": ComplicationEscalationPayload,
    "recovery": RecoveryPayload,
    "decision_execution": DecisionExecutionPayload,
}


def parse_payload(event_type: str, payload: dict):
    cls = _PAYLOAD_REGISTRY.get(event_type)
    if cls is None:
        return payload
    return cls.from_dict(payload)


EVENT_TYPES = [
    "tick",
    "vitals_update",
    "complication",
    "complication_signal",
    "complication_escalation",
    "procedure",
    "state_transition",
    "recovery",
    "decision_execution",
    "decision_options",
    "decision_validation",
    "state.snapshot",
    "system.boot",
]
