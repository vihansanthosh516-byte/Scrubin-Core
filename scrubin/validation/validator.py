from typing import List, Any, Dict
from scrubin.validation.physiology.vitals_models import VitalModel
from scrubin.validation.calibration.trajectory_metrics import TrajectoryMetrics
from scrubin.validation.scoring.realism_score import RealismScorer, RealismResult

class ScientificValidator:
    """
    Main entry point for clinical and scientific calibration of ScrubIn simulations.
    """
    def __init__(self):
        self.scorer = RealismScorer()
        self.metrics = TrajectoryMetrics()

    def validate_session(self, replay_result: Dict[str, Any]) -> RealismResult:
        """
        Analyzes a replayed simulation session for physiological realism.
        """
        final_state = replay_result["final_state"]
        snapshots = replay_result["snapshots"]
        
        # 1. Analyze SpO2 Trajectory
        simulated_spo2 = []
        expected_spo2 = []
        
        for eid, state in snapshots.items():
            sim_val = state.vitals.get("spo2", 98)
            simulated_spo2.append(sim_val)
            
            # Predict what a real patient would do (simplified)
            exp_val = VitalModel.expected_spo2_at_tick(98, "respiratory_failure", state.tick)
            expected_spo2.append(exp_val)
            
        phys_dist = self.metrics.compute_rmse(simulated_spo2, expected_spo2)
        # Normalize RMSE to 0-1 range (simplified)
        normalized_dist = min(1.0, phys_dist / 20.0)
        
        # 2. Analyze Outcome
        outcome_match = True
        if final_state.vitals.get("spo2", 100) < 50:
            outcome_match = (final_state.metadata.get("status") == "DECEASED")
            
        return self.scorer.calculate(
            phys_dist=normalized_dist,
            timing_err=0.1, # Mock timing error
            outcome_match=outcome_match
        )
