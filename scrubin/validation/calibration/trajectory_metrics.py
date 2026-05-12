import math
from typing import List, Dict, Any

class TrajectoryMetrics:
    """
    Computes mathematical distance between simulated and expected clinical curves.
    """
    @staticmethod
    def compute_rmse(simulated: List[float], expected: List[float]) -> float:
        if not simulated or not expected: return 1.0
        n = min(len(simulated), len(expected))
        squared_error = sum((simulated[i] - expected[i])**2 for i in range(n))
        return math.sqrt(squared_error / n)

    @staticmethod
    def compute_timing_error(sim_tick: int, exp_tick: int) -> float:
        return abs(sim_tick - exp_tick) / 60.0 # Error in minutes
