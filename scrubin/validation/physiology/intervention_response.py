from typing import Dict, Any

class InterventionResponse:
    """
    Defines statistical shifts in physiology caused by interventions.
    """
    @staticmethod
    def oxygen_therapy_impact(current_spo2: int, flow_rate: int) -> float:
        # Expected % increase per minute
        if flow_rate > 10: return 5.0
        if flow_rate > 5: return 2.0
        return 1.0

    @staticmethod
    def intubation_delay_ticks() -> int:
        # Expected delay between decision and physiological impact
        return 30 # 30 seconds
