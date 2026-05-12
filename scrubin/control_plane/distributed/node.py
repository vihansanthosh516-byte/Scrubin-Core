from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import uuid

class NodeStatus(Enum):
    ACTIVE = auto()
    DEGRADED = auto()
    OFFLINE = auto()

@dataclass
class CapabilityProfile:
    max_concurrent_jobs: int = 10
    supported_job_types: List[str] = field(default_factory=lambda: ["HIERARCHICAL_SIM", "VECTOR_BATCH"])
    memory_budget_gb: int = 16
    latency_class: str = "LOW_LATENCY" # LOW_LATENCY, STANDARD, HIGH_THROUGHPUT

class ExecutionNode:
    """
    Represents a single execution worker in the distributed clinical OS.
    """
    def __init__(self, node_id: Optional[str] = None):
        self.node_id = node_id or f"node-{uuid.uuid4().hex[:8]}"
        self.status = NodeStatus.ACTIVE
        self.capabilities = CapabilityProfile()
        self.current_load = 0
        self.last_heartbeat = 0.0

    def get_profile(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "status": self.status.name,
            "load": self.current_load,
            "capabilities": {
                "max_jobs": self.capabilities.max_concurrent_jobs,
                "latency": self.capabilities.latency_class
            }
        }
