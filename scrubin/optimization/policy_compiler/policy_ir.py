from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class CausalRuleIR:
    """
    Intermediate Representation of a clinical intervention rule.
    Maps system-level observations to specific causal interventions.
    """
    rule_id: str
    condition: str # e.g. "utilization > 0.85"
    intervention: str # e.g. "increase_triage"
    magnitude: float
    causal_anchor: str # Reference to the CEG node that justified this rule

class PolicyIR:
    """
    Executable collection of compiled causal rules.
    Acts as the 'assembly language' for healthcare network control.
    """
    def __init__(self):
        self.rules: List[CausalRuleIR] = []

    def add_rule(self, rule: CausalRuleIR):
        self.rules.append(rule)
        
    def serialize(self) -> List[Dict[str, Any]]:
        return [vars(r) for r in self.rules]
