from typing import Any, Dict
from scrubin.optimization.objective.reward_model import RewardModel
from scrubin.optimization.objective.constraint_model import ConstraintModel
from scrubin.optimization.objective.calibration_penalty import CalibrationPenalty

class ObjectiveBuilder:
    """
    Composes task performance, scientific constraints, and stability penalties 
    into a final RL training signal.
    """
    def __init__(self):
        self.reward_model = RewardModel()
        self.constraint_model = ConstraintModel()
        self.calibration_penalty = CalibrationPenalty()

    def compute(self, trajectory: Any, outcome: str, realism_score: float, drift_report: Dict[str, Any]) -> float:
        # 1. Clinical Success Reward
        reward = self.reward_model.compute(trajectory, outcome)
        
        # 2. Scientific Boundary Constraint
        # (Using drift metrics from the report for current evaluation)
        constraint = self.constraint_model.evaluate(realism_score, drift_report.get("per_case_drift", {}))
        
        # 3. Longitudinal Stability Penalty
        penalty = self.calibration_penalty.compute(drift_report)
        
        # Final Formula: Reward - Constraint - Penalty
        final_reward = reward - constraint - penalty
        
        # Hard clamp to [-1, 1]
        return max(-1.0, min(1.0, final_reward))
