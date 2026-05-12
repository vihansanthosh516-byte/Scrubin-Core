from typing import Any, Dict, Tuple, Optional
from scrubin.optimization.rl.adapter import ActionAdapter
from scrubin.optimization.rl.observation_builder import ObservationBuilder
from scrubin.optimization.rl.action_space import ClinicalAction
from scrubin.optimization.objective.objective_builder import ObjectiveBuilder
from scrubin.validation.ci_exports.stability_runner import run_stability_check

class ScrubInRLEnvironment:
    """
    Gym-like constrained environment for ScrubIn clinical RL.
    Every step is validated against scientific and stability constraints.
    """
    def __init__(self, kernel: Any):
        self.kernel = kernel
        self.adapter = ActionAdapter()
        self.obs_builder = ObservationBuilder()
        self.objective = ObjectiveBuilder()
        self.t = 0
        self.session_id = "rl-env-session"

    def reset(self, scenario: Optional[str] = None) -> Dict[str, Any]:
        # Reset simulation kernel
        # (In a real system, we'd trigger kernel.reset())
        self.t = 0
        return self._build_observation()

    def step(self, action: ClinicalAction) -> Tuple[Dict[str, Any], float, bool, Dict[str, Any]]:
        # 1. Apply Action via Adapter
        event_payload = self.adapter.encode(action, self.t)
        self.kernel.event_stream.publish(
            "planner.mcts_trace", # Generic action channel
            event_payload,
            tick=self.t,
            session_id=self.session_id
        )

        # 2. Advance Simulation (Internal step)
        self.t += 1
        
        # 3. Phase 14 Stability/Calibration Check
        calibration_report = run_stability_check(self.kernel, None)
        
        # Get replay result for current trace to assess realism
        replay_result = self.kernel.replay.reconstruct_session(self.session_id)
        
        # Calculate Realism via Phase 13 validator
        from scrubin.validation.validator import ScientificValidator
        validator = ScientificValidator()
        realism_result = validator.validate_session(replay_result)

        # 4. HARD STOP: If calibration/stability fails OR realism collapses, terminate
        if calibration_report["status"] == "FAIL" or realism_result.score > 0.4:
            # Episode terminates with high penalty
            return self._build_observation(), -1.0, True, {"reason": "CALIBRATION_FAILURE", "score": realism_result.score}

        # 5. Compute Phase 15.1 Objective Reward
        reward = self.objective.compute(
            trajectory=None,
            outcome=replay_result["final_state"].metadata.get("status", "STABLE"),
            realism_score=realism_result.score,
            drift_report=calibration_report
        )

        # 6. Check Termination
        done = (self.t >= 100) or (replay_result["final_state"].metadata.get("status") == "DECEASED")

        return self._build_observation(), reward, done, {"calibration": calibration_report}

    def _build_observation(self) -> Dict[str, Any]:
        # Get latest state from kernel replay (ground truth for obs)
        result = self.kernel.replay.reconstruct_session(self.session_id)
        return self.obs_builder.build(result["final_state"])
