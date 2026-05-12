from typing import Dict, Any

class HospitalGraph:
    """
    Healthcare network topology: Defines the connections between hospitals.
    Acts as a static deterministic graph derived from the global seed.
    """
    def __init__(self):
        self.hospitals: Dict[str, Any] = {}
        self.edges: Dict[tuple, float] = {}

    def add_hospital(self, hospital_id: str, world_engine: Any):
        self.hospitals[hospital_id] = world_engine

    def connect(self, h1_id: str, h2_id: str, weight: float = 1.0):
        self.edges[(h1_id, h2_id)] = weight
        self.edges[(h2_id, h1_id)] = weight

    def get_neighbors(self, hospital_id: str) -> Dict[str, float]:
        return {k[1]: v for k, v in self.edges.items() if k[0] == hospital_id}
