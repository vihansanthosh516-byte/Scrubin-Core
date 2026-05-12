from enum import Enum
from dataclasses import dataclass
from typing import Optional

class FailureMode(Enum):
    LINEAR = "linear_failure"
    COMBINATORIAL = "combinatorial_interaction"
    CASCADING = "cascading_amplification"
    CAUSAL_COLLAPSE = "causal_graph_collapse"
    DRIFT_ACCUMULATION = "replay_drift_accumulation"

@dataclass
class FailureAnalysis:
    mode: FailureMode
    origin_layer: int
    root_cause: str
    amplification_factor: float = 1.0
