from typing import Dict, Any, Optional
from scrubin.optimization.population.network.hospital_graph import HospitalGraph

class PatientRouter:
    """
    Healthcare Network Routing: Maps population patients to hospitals.
    Deterministic function of patient state and hospital capacity.
    """
    def route(self, patient_id: str, severity: float, network: HospitalGraph) -> str:
        best_hospital = None
        min_load = float("inf")
        
        # Sort keys to ensure deterministic iteration order
        for h_id in sorted(network.hospitals.keys()):
            hospital = network.hospitals[h_id]
            # simplified load score: current_patients / capacity
            load = hospital.get_current_load()
            
            if load < min_load:
                min_load = load
                best_hospital = h_id
                
        return best_hospital or sorted(network.hospitals.keys())[0]
