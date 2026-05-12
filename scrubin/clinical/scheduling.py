from dataclasses import dataclass, field
from typing import Dict, List, Any

@dataclass
class ScheduledProcedure:
    id: str
    target_patient: str
    action_name: str
    ticks_remaining: int
    payload: Dict[str, Any]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "target_patient": self.target_patient,
            "action_name": self.action_name,
            "ticks_remaining": self.ticks_remaining,
            "payload": dict(sorted(self.payload.items())) if self.payload else {},
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ScheduledProcedure":
        return cls(
            id=d["id"],
            target_patient=d.get("target_patient", ""),
            action_name=d.get("action_name", ""),
            ticks_remaining=d.get("ticks_remaining", 0),
            payload=d.get("payload", {}),
        )


@dataclass
class QueueState:
    pending_procedures: List[ScheduledProcedure] = field(default_factory=list)
    emergency_queue: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "pending_procedures": [p.to_dict() for p in self.pending_procedures],
            "emergency_queue": list(self.emergency_queue),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "QueueState":
        return cls(
            pending_procedures=[
                ScheduledProcedure.from_dict(p) if isinstance(p, dict) else p
                for p in d.get("pending_procedures", [])
            ],
            emergency_queue=d.get("emergency_queue", []),
        )
    
    def evolve(self) -> List[ScheduledProcedure]:
        completed = []
        remaining = []
        
        for proc in self.pending_procedures:
            proc.ticks_remaining -= 1
            if proc.ticks_remaining <= 0:
                completed.append(proc)
            else:
                remaining.append(proc)
                
        self.pending_procedures = remaining
        return completed
        
    def schedule(self, proc: ScheduledProcedure):
        self.pending_procedures.append(proc)
