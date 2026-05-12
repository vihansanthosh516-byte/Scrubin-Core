from dataclasses import dataclass
from typing import Dict, List

@dataclass
class GlobalAction:
    routing_bias: Dict[str, float] # hospital_id -> shift
    triage_threshold: float        # global clinical threshold offset
    resource_allocation: Dict[str, int] # resource_type -> target_hospital_id
    epidemic_response_level: int   # 0 to 5

class GlobalActionSpace:
    """
    Defines the system-level interventions available to the Global Policy.
    Prohibits direct clinical or physiological mutation.
    """
    @staticmethod
    def create_action(routing: Dict, triage: float, response: int) -> GlobalAction:
        return GlobalAction(
            routing_bias=routing,
            triage_threshold=triage,
            resource_allocation={},
            epidemic_response_level=response
        )
