import random
from typing import List
from scrubin.world.model import SimulationWorld

class RolloutPolicy:
    """
    Heuristic policy to guide MCTS rollouts and avoid exhaustive brute force.
    """
    @staticmethod
    def select_action(world: SimulationWorld, available_actions: List[str]) -> str:
        vitals = world.physiology.vitals
        
        spo2 = vitals.get("spo2", 100)
        map_pressure = (vitals.get("bp_systolic", 120) + 2 * vitals.get("bp_diastolic", 80)) / 3.0
        
        # Guided heuristics
        if spo2 < 85 and "intubation" in available_actions:
            # 80% chance to follow heuristic
            if random.random() < 0.8:
                return "intubation"
        elif spo2 < 92 and "oxygen_therapy" in available_actions:
            if random.random() < 0.7:
                return "oxygen_therapy"
                
        if map_pressure < 65 and "vasopressors" in available_actions:
            if random.random() < 0.8:
                return "vasopressors"
        elif map_pressure < 75 and "iv_fluids" in available_actions:
            if random.random() < 0.7:
                return "iv_fluids"
                
        return random.choice(available_actions)
