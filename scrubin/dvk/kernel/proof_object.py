from dataclasses import dataclass
from typing import Optional
import hashlib, json

@dataclass(frozen=True)
class ExecutionProofObject:
    """
    Immutable, hash-locked certificate of execution correctness.
    This is the ONLY artifact AG consumes from ScrubIn.
    """
    run_id: str

    ces_program_hash: str
    initial_state_hash: str
    final_state_hash: str
    causal_graph_hash: str

    determinism_verified: bool
    replay_equivalent: bool
    constraint_satisfied: bool
    governance_valid: bool
    rl_safe: bool

    counterfactual_consistency_hash: str
    global_policy_fingerprint: str
    execution_trace_hash: str

    previous_proof_hash: Optional[str]
    current_proof_hash: str

    @property
    def valid(self) -> bool:
        return (self.determinism_verified and
                self.replay_equivalent and
                self.constraint_satisfied and
                self.governance_valid and
                self.rl_safe)

    def to_dict(self):
        return {
            "run_id": self.run_id,
            "valid": self.valid,
            "ces_program_hash": self.ces_program_hash[:16],
            "final_state_hash": self.final_state_hash[:16],
            "current_proof_hash": self.current_proof_hash[:16],
            "determinism": self.determinism_verified,
            "replay": self.replay_equivalent,
            "constraints": self.constraint_satisfied,
            "governance": self.governance_valid,
            "rl_safe": self.rl_safe,
        }

def compute_epo_hash(run_id: str, ces_hash: str, state_hash: str,
                     trace_hash: str, prev_hash: str) -> str:
    payload = f"{run_id}:{ces_hash}:{state_hash}:{trace_hash}:{prev_hash}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
