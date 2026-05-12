from dataclasses import dataclass

@dataclass
class RealismResult:
    score: float # 0.0 (Perfect) to 1.0 (Unrealistic)
    physiological_distance: float
    timing_accuracy: float
    outcome_match: bool

class RealismScorer:
    """
    Collapses multiple clinical metrics into a single realism score.
    """
    def calculate(self, phys_dist: float, timing_err: float, outcome_match: bool) -> RealismResult:
        # Weighted sum of errors
        base_score = (phys_dist * 0.6) + (min(1.0, timing_err) * 0.4)
        if not outcome_match:
            base_score = min(1.0, base_score + 0.3)
            
        return RealismResult(
            score=round(base_score, 3),
            physiological_distance=phys_dist,
            timing_accuracy=timing_err,
            outcome_match=outcome_match
        )
