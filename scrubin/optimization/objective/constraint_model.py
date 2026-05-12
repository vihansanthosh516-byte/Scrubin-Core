from typing import Dict, Any

class ConstraintModel:
    """
    Enforces Phase 14 clinical boundaries within the optimization loop.
    Ensures RL stays within scientifically valid territory.
    """
    def evaluate(self, calibration_score: float, drift_metrics: Dict[str, Any]) -> float:
        penalty = 0.0
        
        # Hard Rule: Realism Threshold
        # (Assuming realism_score 0.0 is perfect, 1.0 is failure)
        # Convert Phase 13 score to penalty
        if calibration_score > 0.4: # Failure threshold from Phase 13 demo
            penalty += 1.0
            
        # Hard Rule: Any significant drift
        max_drift = max(drift_metrics.values()) if drift_metrics else 0.0
        if max_drift > 0.1:
            penalty += 1.0
            
        return min(1.0, penalty)
