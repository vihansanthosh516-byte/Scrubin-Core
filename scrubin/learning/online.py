from typing import Any
try:
    import numpy as np
except ImportError:
    class MockNumpy:
        def mean(self, x): return sum(x) / len(x) if x else 0
    np = MockNumpy()
from typing import List, Dict, Any, Optional

class OnlineLearner:
    """
    Handles real-time adaptation of clinical policies based on streaming data.
    """
    def __init__(self, learning_rate: float = 0.01):
        self.learning_rate = learning_rate
        self.policy_weights: Dict[str, float] = {}
        self.performance_history: List[float] = []
        self.drift_detected = False

    def update_policy(self, action: str, outcome_utility: float):
        """
        Incremental update of action preference.
        """
        if action not in self.policy_weights:
            self.policy_weights[action] = 0.0
            
        # Simple reinforcement learning update
        error = outcome_utility - self.policy_weights[action]
        self.policy_weights[action] += self.learning_rate * error
        
        self.performance_history.append(outcome_utility)
        self._check_for_drift()

    def _check_for_drift(self, window_size: int = 50):
        """
        Detects if the environment has changed (nonstationarity).
        """
        if len(self.performance_history) < window_size * 2:
            return
            
        recent = np.mean(self.performance_history[-window_size:])
        older = np.mean(self.performance_history[-window_size*2:-window_size])
        
        # If performance drops significantly, signal drift
        if older - recent > 0.2: # Threshold
            self.drift_detected = True
            print("[OnlineLearner] Environment drift detected! Adjusting confidence.")

    def get_confidence_multiplier(self) -> float:
        return 0.5 if self.drift_detected else 1.0
