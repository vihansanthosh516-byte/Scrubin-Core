from typing import Dict, Any, List

class HospitalAggregator:
    """
    Compresses atomic hospital states into system-level utilization and pressure vectors.
    Ensures zero leakage of patient-level clinical data.
    """
    def aggregate(self, hospital_graph: Any) -> Dict[str, List[float]]:
        utilization = []
        icu_pressure = []
        backlog = []
        
        # Sort by ID for deterministic tensor ordering
        for h_id in sorted(hospital_graph.hospitals.keys()):
            h = hospital_graph.hospitals[h_id]
            # Util % = occupied / total_capacity
            util = getattr(h, "occupancy", 0.8) # Mocked
            pressure = 1.0 if util > 0.9 else 0.0
            
            utilization.append(util)
            icu_pressure.append(pressure)
            backlog.append(getattr(h, "queue_size", 5) / 20.0) # Normalized
            
        return {
            "utilization_vector": utilization,
            "pressure_vector": icu_pressure,
            "backlog_vector": backlog
        }
