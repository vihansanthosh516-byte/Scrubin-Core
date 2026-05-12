from typing import Dict, Any
from scrubin.control_plane.streaming.channels import Topics

class GoldReplayCases:
    """
    Canonical reference trajectories for verifying clinical simulation reality.
    """
    @staticmethod
    def icu_deterioration_recovery(kernel: Any, session_id: str):
        """
        Gold Case 001: ICU Deterioration -> Intervention -> Recovery.
        """
        # 1. Baseline
        kernel.event_stream.publish(Topics.PATIENT_VITALS, {"patient_id": "gold-1", "hr": 80, "spo2": 98}, tick=100, session_id=session_id)
        
        # 2. Deterioration
        kernel.event_stream.publish(Topics.PATIENT_VITALS, {"patient_id": "gold-1", "hr": 120, "spo2": 82}, tick=105, session_id=session_id)
        
        # 3. Intervention (Planner)
        kernel.event_stream.publish(Topics.MCTS_TRACE, {"category": "PLANNER", "chosen_action": "O2_THERAPY"}, tick=106, session_id=session_id)
        
        # 4. Recovery
        kernel.event_stream.publish(Topics.PATIENT_VITALS, {"patient_id": "gold-1", "hr": 90, "spo2": 96}, tick=110, session_id=session_id)
