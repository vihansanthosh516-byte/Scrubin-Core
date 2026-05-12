from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

@dataclass
class PatientCardDTO:
    patient_id: str
    hr: int
    spo2: int
    status: str
    mortality_risk: float

@dataclass
class ClusterHealthDTO:
    active_nodes: int
    throughput: float
    avg_latency: float
    system_status: str

@dataclass
class AlertDTO:
    id: str
    severity: str
    message: str
    tick: int
    timestamp: float

def to_json(dto: Any) -> Dict[str, Any]:
    return asdict(dto)
