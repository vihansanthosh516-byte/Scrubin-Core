from typing import List, Dict, Any
from scrubin.optimization.policy_compiler.policy_ir import CausalRuleIR

class CausalRuleExtractor:
    """
    Synthesizes executable rules from counterfactual delta graphs.
    Identifies stable causal patterns: (Policy Action) -> (Outcome Delta).
    """
    def extract_rules(self, causal_deltas: List[Dict[str, Any]]) -> List[CausalRuleIR]:
        rules = []
        for i, delta in enumerate(causal_deltas):
            # 1. Identify positive deltas (e.g. mortality reduction)
            if delta.get("mortality_delta", 0) < 0:
                # 2. Extract the intervention that caused it
                # (Simplified mapping for demo)
                rules.append(CausalRuleIR(
                    rule_id=f"RULE_{i}",
                    condition="system_overload > 0.8",
                    intervention="ADJUST_TRIAGE",
                    magnitude=0.15,
                    causal_anchor="ceg_node_delta_X"
                ))
        return rules
