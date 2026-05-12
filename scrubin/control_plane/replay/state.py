from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import copy

@dataclass
class ReplayState:
    """
    Serializable state model for deterministic clinical replay.
    """
    tick: int = 0
    vitals: Dict[str, Any] = field(default_factory=dict)
    resources: Dict[str, Any] = field(default_factory=dict)
    decisions: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class StateMutator:
    """
    Pure functions to apply semantic events to a ReplayState.
    """
    def apply(self, event: Any, state: ReplayState) -> ReplayState:
        # Create a deep copy to ensure purity and isolation
        new_state = copy.deepcopy(state)
        new_state.tick = max(new_state.tick, event.timestamp_tick)
        
        topic = event.topic
        payload = event.payload
        
        if topic == "patient.vitals":
            new_state.vitals.update(payload)
        elif topic == "planner.mcts_trace":
            new_state.decisions.append(payload)
        elif topic == "cluster.resource_alerts":
            new_state.resources.update(payload)
        elif topic == "clinical.mortality":
            new_state.metadata["status"] = "DECEASED"
            
        return new_state
