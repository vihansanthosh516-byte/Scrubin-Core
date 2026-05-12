import math
from typing import Dict, Any, List

class VitalModel:
    """
    Defines expected statistical distributions for patient vitals.
    """
    @staticmethod
    def spo2_decay_rate(condition: str) -> float:
        # Expected % drop per minute
        rates = {
            "healthy": 0.01,
            "respiratory_failure": 2.5,
            "sepsis": 0.5,
            "shock": 1.0
        }
        return rates.get(condition, 0.1)

    @staticmethod
    def expected_spo2_at_tick(start_val: int, condition: str, tick_delta: int) -> float:
        # Simple exponential decay model for validation
        decay = VitalModel.spo2_decay_rate(condition) / 60.0 # per tick (assuming 1s ticks)
        return start_val * math.exp(-decay * tick_delta)

    @staticmethod
    def hr_compensation(spo2: int) -> int:
        """
        Calculates expected heart rate compensation for hypoxia.
        """
        if spo2 > 95: return 80
        if spo2 > 90: return 95
        if spo2 > 85: return 110
        return 130
