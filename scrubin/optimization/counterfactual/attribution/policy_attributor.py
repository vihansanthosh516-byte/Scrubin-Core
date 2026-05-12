from typing import Dict, Any, List

class PolicyAttributor:
    """
    Answers: "Which specific policy lever caused this outcome change?"
    Links GlobalActions to CEG modifications and downstream clinical deltas.
    """
    def attribute_impact(self, delta: Dict[str, Any], action_variant: Any) -> Dict[str, float]:
        scores = {}
        
        # Heuristic: If mortality changed and triage was adjusted
        if delta.get("mortality_delta") != 0:
            if hasattr(action_variant, "triage_threshold"):
                scores["triage_threshold"] = 0.85 # High attribution
                
        return scores
