from dataclasses import dataclass, field
from typing import List, Dict, Any
from scrubin.learning.metrics import compute_all_metrics, CompositeMetrics


@dataclass
class TraineePerformance:
    session_id: str
    trainee_id: str
    scenario_name: str
    overall_score: float
    metrics: CompositeMetrics
    decision_speed_score: float
    accuracy_score: float
    resource_score: float
    findings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "trainee_id": self.trainee_id,
            "scenario_name": self.scenario_name,
            "overall_score": round(self.overall_score, 6),
            "metrics": self.metrics.to_dict(),
            "decision_speed_score": round(self.decision_speed_score, 6),
            "accuracy_score": round(self.accuracy_score, 6),
            "resource_score": round(self.resource_score, 6),
            "findings": self.findings,
        }


class TraineeScoringEngine:
    def __init__(self):
        pass

    def evaluate_session(self, session_data: dict) -> TraineePerformance:
        """
        Evaluate a trainee's performance based on session logs.
        """
        trajectories = session_data.get("trajectories", [])
        num_violations = session_data.get("num_violations", 0)
        
        # 1. Calculate standard clinical/safety/resource metrics
        composite = compute_all_metrics(trajectories, num_violations=num_violations)
        
        # 2. Calculate decision speed (average time per critical action)
        # For simplicity, we use a placeholder logic here
        decision_speed = 0.85 
        
        # 3. Calculate Accuracy (matching expert/gold standard actions)
        accuracy = composite.clinical.survival_rate * 0.7 + (1.0 - composite.clinical.mean_mortality_final) * 0.3
        
        # 4. Final Score
        overall = (composite.composite_score * 0.6) + (decision_speed * 0.2) + (accuracy * 0.2)
        
        findings = []
        if composite.clinical.survival_rate < 1.0:
            findings.append("Critical failure: Patient did not survive.")
        if num_violations > 0:
            findings.append(f"Safety violations detected: {num_violations}")
        if composite.resource.overtreatment_rate > 0.4:
            findings.append("Resource inefficiency: High overtreatment rate.")

        return TraineePerformance(
            session_id=session_data.get("session_id", "unknown"),
            trainee_id=session_data.get("trainee_id", "anonymous"),
            scenario_name=session_data.get("scenario_name", "unnamed"),
            overall_score=overall,
            metrics=composite,
            decision_speed_score=decision_speed,
            accuracy_score=accuracy,
            resource_score=1.0 - composite.resource.overtreatment_rate,
            findings=findings
        )
