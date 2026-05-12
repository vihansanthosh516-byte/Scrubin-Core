import random
from typing import Dict, Any
from scrubin.optimization.global_policy.action_space import GlobalAction

class GlobalPolicyEngine:
    """
    Seed-deterministic meta-policy for clinical network orchestration.
    Intervenes at the system structure level, not the patient level.
    """
    def act(self, system_obs: Dict[str, Any], seed: int) -> GlobalAction:
        random.seed(seed)
        
        # 1. Analyze Obs
        utilization = system_obs.get("utilization_vector", [0.5])
        avg_util = sum(utilization) / len(utilization) if utilization else 0.5
        
        # 2. Heuristic/Learned Meta-Decision (Simplified for demo)
        triage_shift = 0.0
        if avg_util > 0.8:
            triage_shift = 0.15 # Tighten triage under load
            
        return GlobalAction(
            routing_bias={},
            triage_threshold=triage_shift,
            resource_allocation={},
            epidemic_response_level=1 if avg_util > 0.7 else 0
        )
