from typing import Any, Dict

class CalibrationPenalty:
    """
    Bridges Phase 14 stability reporting into the RL objective signal.
    """
    def compute(self, calibration_report: Dict[str, Any]) -> float:
        # report contains "global_stability_index" and "worst_case_drift"
        stability_index = calibration_report.get("global_stability_index", 1.0)
        max_drift = calibration_report.get("worst_case_drift", 0.0)
        
        # Stability penalty (higher index = better stability)
        penalty = (1.0 - stability_index)
        
        # Drift amplification
        if max_drift > 0.05:
            penalty += (max_drift * 2.0)
            
        return min(1.0, penalty)
