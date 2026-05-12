from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class DriftResult:
    global_drift: float
    per_case_drift: Dict[str, float]
    worst_case: Optional[str]

class CalibrationDriftEngine:
    """
    Tracks how simulation realism scores change relative to stored baselines.
    """
    def compute_drift(self, baseline_scores: Dict[str, float], new_scores: Dict[str, float]) -> DriftResult:
        per_case_drift = {}
        total_drift = 0.0
        worst_case = None
        max_drift = -1.0
        
        for cid, score in new_scores.items():
            baseline = baseline_scores.get(cid, score)
            drift = score - baseline # positive = regression (score 0 is perfect)
            per_case_drift[cid] = drift
            total_drift += drift
            
            if abs(drift) > max_drift:
                max_drift = abs(drift)
                worst_case = cid
                
        avg_drift = total_drift / len(new_scores) if new_scores else 0.0
        return DriftResult(
            global_drift=avg_drift,
            per_case_drift=per_case_drift,
            worst_case=worst_case
        )
