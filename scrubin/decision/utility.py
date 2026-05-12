from dataclasses import dataclass
from scrubin.world.model import SimulationWorld

@dataclass
class UtilityWeights:
    survival_weight: float = 100.0
    organ_preservation_weight: float = 20.0
    resource_efficiency_weight: float = 5.0
    stability_weight: float = 10.0
    confidence_weight: float = 2.0

class UtilityFunction:
    """
    Centralized utility evaluation for all strategic planning.
    Converts a deterministic world state into a single float optimization target.
    """
    def __init__(self, weights: UtilityWeights = None):
        self.weights = weights or UtilityWeights()
        
    def evaluate(self, world: SimulationWorld) -> float:
        # 1. Survival Utility (Base survival probability = 1.0 - mortality_risk)
        survival_prob = 1.0 - world.mortality_risk
        survival_gain = survival_prob * self.weights.survival_weight
        
        # 2. Organ Preservation
        organs = world.organ_state
        organ_health_avg = (organs.cardiovascular.health + organs.respiratory.health + organs.renal.health) / 3.0
        organ_gain = organ_health_avg * self.weights.organ_preservation_weight
        
        # 3. Resource Efficiency Penalty
        # Count how many total resources are currently used
        used_resources = sum(r.currently_used for r in world.resource_manager.resources.values())
        resource_penalty = used_resources * self.weights.resource_efficiency_weight
        
        # 4. Instability Penalty (SOFA and NEWS2)
        # Higher score = worse stability
        instability = (world.sofa_score + world.news2_score)
        instability_penalty = instability * self.weights.stability_weight
        
        return survival_gain + organ_gain - resource_penalty - instability_penalty
