from typing import List, Any

class TransmissionModel:
    """
    Population-level disease dynamics: Computes infection risk deterministically.
    Ensures disease spread is a pure functional transformation of state.
    """
    def compute_risk(self, patient_state: Any, contact_load: float) -> float:
        # base_infection + (infectiousness * contact_rate)
        # simplified for deterministic simulation
        infection_risk = patient_state.get("infection_load", 0.0) + contact_load
        return min(1.0, infection_risk)

class SeverityModel:
    """
    Maps population infection state to clinical ICU demand.
    """
    def calculate_severity(self, load: float, age: int) -> float:
        return (load * 0.5) + (age / 100.0 * 0.5)
