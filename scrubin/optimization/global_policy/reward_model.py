from typing import Dict, Any

class GlobalRewardModel:
    """
    Computes system-level objectives for healthcare network optimization.
    Focuses on population survival, resource efficiency, and stability.
    """
    def compute(self, population_stats: Dict[str, Any], hospital_stats: Dict[str, Any]) -> float:
        # 1. Mortality Penalty
        mortality = population_stats.get("mortality_rate", 0.0)
        
        # 2. Survival Reward
        survival = 1.0 - mortality
        
        # 3. Overload Penalty
        overload = max(hospital_stats.get("utilization_vector", [0.0]))
        overload_penalty = 0.5 if overload > 0.95 else 0.0
        
        # Global Reward: weighted sum of network health
        reward = (survival * 0.7) - (overload_penalty * 0.3)
        
        return max(-1.0, min(1.0, reward))
