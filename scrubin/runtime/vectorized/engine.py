from typing import Any
try:
    import numpy as np
except ImportError:
    class MockNumpy:
        class MockRandom:
            def normal(self, **kwargs): 
                size = kwargs.get('size', (1,1))
                return [[0.0 for _ in range(size[1])] for _ in range(size[0])] if isinstance(size, tuple) else [0.0] * size
        def __init__(self):
            self.random = self.MockRandom()
        def mean(self, x, axis=None): return 0.0
        def sum(self, x, axis=None): return 0.0
        def clip(self, x, a, b): return x
        ndarray = Any
    np = MockNumpy()
try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

class VectorizedSimulation:
    """
    Simulates thousands of patients in parallel using vectorized operations.
    """
    def __init__(self, num_patients: int):
        self.num_patients = num_patients
        self.states = self._initialize_states()

    def _initialize_states(self) -> np.ndarray:
        # State vector: [SpO2, HR, SBP, DBP, Temperature] for each patient
        return np.random.normal(loc=[98, 80, 120, 80, 37], scale=[2, 10, 10, 5, 0.5], size=(self.num_patients, 5))

    def evolve(self):
        """
        Advance all patients by one tick using vectorized math.
        """
        # Simple random walk for vitals
        drift = np.random.normal(loc=0, scale=0.1, size=(self.num_patients, 5))
        self.states += drift
        
        # Apply constraints (e.g., SpO2 max 100)
        self.states[:, 0] = np.clip(self.states[:, 0], 0, 100)

    def apply_batch_intervention(self, patient_indices: np.ndarray, effect_vector: np.ndarray):
        """
        Apply an intervention to a subset of patients.
        """
        self.states[patient_indices] += effect_vector

    def get_summary_metrics(self) -> dict:
        return {
            "mean_spo2": np.mean(self.states[:, 0]),
            "mean_hr": np.mean(self.states[:, 1]),
            "critical_count": np.sum(self.states[:, 0] < 85)
        }
