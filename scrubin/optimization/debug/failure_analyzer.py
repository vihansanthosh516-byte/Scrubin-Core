from typing import Dict, Any, List
from scrubin.optimization.debug.episode_trace import EpisodeTrace

class FailureAnalyzer:
    """
    Classifies raw clinical episode failures into explainable semantic causes.
    """
    def analyze(self, episode_trace: EpisodeTrace) -> Dict[str, Any]:
        if not episode_trace.steps: return {"type": "UNKNOWN"}
        
        last_step = episode_trace.steps[-1]
        
        # Taxonomy-based classification
        if last_step.calibration_score > 0.4:
            return {
                "type": "CALIBRATION_FAILURE",
                "explanation": "Simulation drifted from physiological reality (Phase 14 gate tripped)",
                "root_step": last_step.step_id
            }
            
        if last_step.observation.get("status") == "DECEASED":
            # Check for delay in interventions
            return {
                "type": "PHYSIOLOGICAL_COLLAPSE",
                "explanation": "Patient vitals reached terminal threshold before stabilization",
                "root_step": last_step.step_id
            }
            
        return {"type": "SUCCESS", "final_reward": episode_trace.get_final_reward()}
