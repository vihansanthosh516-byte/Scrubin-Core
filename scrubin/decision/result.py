from dataclasses import dataclass, field
from typing import Any

@dataclass
class PlanningResult:
    selected_action: str
    expected_utility: float
    projected_mortality: float
    projected_sofa: float
    
    explored_nodes: int
    search_depth: int
    confidence: float
    
    reasoning_trace: list[str] = field(default_factory=list)
    branches_considered: list[Any] = field(default_factory=list)
