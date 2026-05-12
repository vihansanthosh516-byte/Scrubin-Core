from dataclasses import dataclass, field

@dataclass
class DecisionTrace:
    action_selected: str
    expected_utility: float
    mortality_reduction: float
    organ_preservation_score: float
    resource_impact: str
    reasons: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "action": self.action_selected,
            "utility": self.expected_utility,
            "mortality_reduction": self.mortality_reduction,
            "reasons": self.reasons
        }

class TraceGenerator:
    @staticmethod
    def generate_trace(action: str, root_world, predicted_world, base_utility, new_utility) -> DecisionTrace:
        mortality_delta = root_world.mortality_risk - predicted_world.mortality_risk
        
        reasons = []
        if mortality_delta > 0.1:
            reasons.append(f"Substantially reduced projected mortality ({-mortality_delta:.2f})")
        elif mortality_delta > 0:
            reasons.append(f"Marginally improved survival probability")
            
        organ_health_delta = (predicted_world.organ_state.cardiovascular.health - root_world.organ_state.cardiovascular.health)
        if organ_health_delta > 0:
            reasons.append("Preserved cardiovascular stability")
            
        if action == "intubation":
            reasons.append("Ventilator scarcity acceptable given hypoxia risk")
            
        return DecisionTrace(
            action_selected=action,
            expected_utility=new_utility,
            mortality_reduction=mortality_delta,
            organ_preservation_score=organ_health_delta,
            resource_impact="Nominal",
            reasons=reasons if reasons else ["Chosen as best available utility path"]
        )
