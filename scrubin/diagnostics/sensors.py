import random
from typing import Dict, Any


class SensorModel:
    def __init__(self, noise_level: float = 0.02, bias: float = 0.0, seed: int = 42):
        self.noise_level = noise_level
        self.bias = bias
        self._rng = random.Random(seed)

    def observe(self, true_value: float) -> float:
        """
        Returns a noisy observation of the true value.
        Uses Gaussian noise proportional to the value.
        """
        if true_value == 0:
            return 0.0
        # Standard deviation is noise_level * true_value
        noise = self._rng.gauss(0, self.noise_level * abs(true_value))
        return true_value + self.bias + noise


class ObservationEngine:
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.sensors: Dict[str, SensorModel] = {
            "spo2": SensorModel(noise_level=0.015, seed=seed + 1),
            "bp_systolic": SensorModel(noise_level=0.03, seed=seed + 2),
            "heart_rate": SensorModel(noise_level=0.02, seed=seed + 3),
            "temperature": SensorModel(noise_level=0.005, seed=seed + 4),
            "respiratory_rate": SensorModel(noise_level=0.05, seed=seed + 5),
        }

    def get_observed_vitals(self, true_vitals: Dict[str, float]) -> Dict[str, float]:
        observed = {}
        for key, value in true_vitals.items():
            sensor = self.sensors.get(key, SensorModel(noise_level=0.01, seed=self.seed))
            observed[key] = sensor.observe(value)
        return observed

    def get_confidence_interval(self, key: str, observed_value: float) -> tuple[float, float]:
        """
        Returns a 95% confidence interval for the observation.
        """
        sensor = self.sensors.get(key)
        if not sensor:
            return (observed_value * 0.98, observed_value * 1.02)
        
        # 95% CI is approx +/- 1.96 * sigma
        sigma = sensor.noise_level * abs(observed_value)
        return (observed_value - 1.96 * sigma, observed_value + 1.96 * sigma)
