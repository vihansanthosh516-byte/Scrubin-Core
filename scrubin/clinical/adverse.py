from dataclasses import dataclass
from typing import List, Dict, Optional
import random

@dataclass
class AdverseEffect:
    vital_target: str
    delta: float
    probability: float
    delay_ticks: int = 0

@dataclass
class TherapeuticWindow:
    ideal_start_tick: int
    ideal_end_tick: int
    utility_peak: float
    utility_decay: float
    
    def evaluate(self, current_tick: int) -> float:
        if current_tick < self.ideal_start_tick:
            return self.utility_peak * 0.5 # Premature
        elif self.ideal_start_tick <= current_tick <= self.ideal_end_tick:
            return self.utility_peak # Optimal
        else:
            delay = current_tick - self.ideal_end_tick
            return max(0.0, self.utility_peak - (delay * self.utility_decay))

class AdverseEventModel:
    def __init__(self, seed: int = 42):
        self._rng = random.Random(seed)
        
        # Define adverse profiles for specific interventions
        self._profiles: Dict[str, List[AdverseEffect]] = {
            "vasopressors": [
                AdverseEffect("bp_diastolic", -5.0, 0.2), # Ischemia risk
                AdverseEffect("heart_rate", 15.0, 0.3)    # Arrhythmia risk
            ],
            "intubation": [
                AdverseEffect("bp_systolic", -15.0, 0.15) # Post-intubation hypotension
            ],
            "blood_transfusion": [
                AdverseEffect("temperature", 1.5, 0.05)   # Transfusion reaction
            ]
        }
        
    def evaluate_intervention(self, intervention_id: str) -> List[AdverseEffect]:
        """
        Determines deterministically if an intervention triggers adverse effects.
        """
        triggered = []
        if intervention_id in self._profiles:
            for effect in self._profiles[intervention_id]:
                if self._rng.random() < effect.probability:
                    triggered.append(effect)
        return triggered
