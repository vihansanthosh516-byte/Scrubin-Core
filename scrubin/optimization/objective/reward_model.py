from typing import Any, Dict

class RewardModel:
    """
    Computes clinical utility and task performance rewards.
    Independent of realism/calibration.
    """
    def compute(self, trajectory: Any, outcome: str) -> float:
        reward = 0.0
        
        # 1. Outcome Reward
        if outcome == "SURVIVED":
            reward += 0.8
        elif outcome == "DECEASED":
            reward -= 0.8
            
        # 2. Efficiency (simplified)
        # Assuming trajectory has length or timing info
        reward += 0.1 # Placeholder for efficiency gain
        
        # 3. Resource Usage
        # reward -= 0.05 (penalty for overuse)
        
        return max(-1.0, min(1.0, reward))
