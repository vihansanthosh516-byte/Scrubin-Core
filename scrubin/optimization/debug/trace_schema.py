from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass(frozen=True)
class EpisodeStepTrace:
    """
    Atomic unit of RL episode forensics.
    Maps RL interaction to deterministic simulation state and causality.
    """
    step_id: int
    tick: int
    
    action: Dict[str, Any]
    observation: Dict[str, Any]
    
    reward: float
    calibration_score: float
    
    event_ids: List[str] = field(default_factory=list) # Links to CEG nodes
    state_hash: str = ""
