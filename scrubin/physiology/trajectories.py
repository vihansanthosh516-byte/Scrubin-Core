import math
from abc import ABC, abstractmethod


class VitalTrajectory(ABC):
    def __init__(self, vital: str, start_tick: int, duration: int):
        self.vital = vital
        self.start_tick = start_tick
        self.duration = duration
        self.end_tick = start_tick + duration

    @abstractmethod
    def evaluate(self, current_tick: int) -> float:
        """Returns the delta effect on the vital for the given tick."""
        pass

    def is_active(self, current_tick: int) -> bool:
        return self.start_tick <= current_tick < self.end_tick


class LinearTrajectory(VitalTrajectory):
    def __init__(self, vital: str, start_tick: int, duration: int, total_delta: float):
        super().__init__(vital, start_tick, duration)
        self.total_delta = total_delta
        self.delta_per_tick = total_delta / duration if duration > 0 else 0

    def evaluate(self, current_tick: int) -> float:
        if not self.is_active(current_tick):
            return 0.0
        return self.delta_per_tick


class ExponentialRecoveryCurve(VitalTrajectory):
    def __init__(self, vital: str, start_tick: int, duration: int, initial_delta: float, decay_rate: float = 0.5):
        super().__init__(vital, start_tick, duration)
        self.initial_delta = initial_delta
        self.decay_rate = decay_rate

    def evaluate(self, current_tick: int) -> float:
        if not self.is_active(current_tick):
            return 0.0
        elapsed = current_tick - self.start_tick
        # Effect decays exponentially over time
        return self.initial_delta * math.exp(-self.decay_rate * elapsed)


class SigmoidProcedureEffect(VitalTrajectory):
    def __init__(self, vital: str, start_tick: int, duration: int, total_delta: float):
        super().__init__(vital, start_tick, duration)
        self.total_delta = total_delta

    def evaluate(self, current_tick: int) -> float:
        if not self.is_active(current_tick):
            return 0.0
        elapsed = current_tick - self.start_tick
        # Sigmoid derivative or distributed effect. We'll distribute the total delta
        # such that the peak effect happens in the middle of the duration.
        midpoint = self.duration / 2.0
        steepness = 10.0 / self.duration if self.duration > 0 else 1.0
        
        # We need the delta for THIS tick, which is the difference between the CDF at t and t-1
        def sigmoid(x):
            return 1 / (1 + math.exp(-steepness * (x - midpoint)))
        
        cdf_now = sigmoid(elapsed + 1)
        cdf_prev = sigmoid(elapsed)
        
        return self.total_delta * (cdf_now - cdf_prev)


class DeteriorationCurve(VitalTrajectory):
    def __init__(self, vital: str, start_tick: int, duration: int, rate: float, acceleration: float = 0.0):
        super().__init__(vital, start_tick, duration)
        self.rate = rate
        self.acceleration = acceleration

    def evaluate(self, current_tick: int) -> float:
        if not self.is_active(current_tick):
            return 0.0
        elapsed = current_tick - self.start_tick
        return self.rate + (self.acceleration * elapsed)
