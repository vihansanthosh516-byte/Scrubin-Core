from typing import List, Dict, Any
from scrubin.optimization.policy_compiler.policy_ir import PolicyIR
from scrubin.optimization.policy_compiler.synthesis.causal_rule_extractor import CausalRuleExtractor

class PolicyCompiler:
    """
    Orchestrates the synthesis of executable clinical policies from causal structure.
    Bridges counterfactual forensic results into actionable system-level IR.
    """
    def __init__(self):
        self.extractor = CausalRuleExtractor()

    def compile(self, counterfactual_deltas: List[Dict[str, Any]]) -> PolicyIR:
        """
        Compiler Pipeline: Deltas -> Causal Rule Extraction -> Policy IR Synthesis.
        """
        ir = PolicyIR()
        
        # 1. Synthesize rules from empirical causal evidence
        extracted_rules = self.extractor.extract_rules(counterfactual_deltas)
        
        # 2. Stitch into integrated IR
        for rule in extracted_rules:
            ir.add_rule(rule)
            
        return ir
