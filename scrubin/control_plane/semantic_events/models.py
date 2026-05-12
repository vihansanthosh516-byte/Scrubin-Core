from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import uuid

@dataclass(frozen=True)
class SemanticEvent:
    event_id: str = field(default_factory=lambda: f"ev-{uuid.uuid4().hex[:8]}")
    trace_id: str = "root"
    parent_trace_id: Optional[str] = None
    topic: str = "generic"
    timestamp_tick: int = 0
    session_id: str = "default"
    node_id: str = "local"
    payload: Dict[str, Any] = field(default_factory=dict)
    category: str = "OPERATIONAL" # CLINICAL, PLANNER, INFRASTRUCTURE, GOVERNANCE

@dataclass(frozen=True)
class ClinicalEvent(SemanticEvent):
    category: str = "CLINICAL"

@dataclass(frozen=True)
class PlannerEvent(SemanticEvent):
    category: str = "PLANNER"

@dataclass(frozen=True)
class InfrastructureEvent(SemanticEvent):
    category: str = "INFRASTRUCTURE"

@dataclass(frozen=True)
class GovernanceEvent(SemanticEvent):
    category: str = "GOVERNANCE"
