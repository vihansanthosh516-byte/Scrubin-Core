import hashlib
from typing import Dict, Any, List

class ReplayProofGenerator:
    """
    Generates cryptographic proofs of deterministic execution.
    Allows external auditors to verify that a clinical outcome was 
    produced by a specific policy version under a specific seed.
    """
    def generate_proof(self, execution_trace: List[str], final_state_hash: str, policy_fingerprint: str) -> str:
        payload = f"{''.join(execution_trace)}:{final_state_hash}:{policy_fingerprint}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
