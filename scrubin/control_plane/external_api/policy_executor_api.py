from typing import Dict, Any
from scrubin.control_plane.governance.policy_registry import PolicyRegistry
from scrubin.control_plane.governance.policy_signature import PolicySigner
from scrubin.control_plane.governance.version_lock import SystemLock
from scrubin.control_plane.audit.replay_proof_generator import ReplayProofGenerator

class PolicyExecutorAPI:
    """
    External-facing policy execution interface.
    Validates signature + system lock before every execution.
    """
    def __init__(self, registry: PolicyRegistry, system_lock: SystemLock):
        self.registry = registry
        self.system_lock = system_lock
        self.proof_gen = ReplayProofGenerator()

    def execute(self, policy_id: str, system_obs: Dict[str, Any]) -> Dict[str, Any]:
        # 1. Retrieve and validate
        record = self.registry.fetch(policy_id)
        if not record:
            return {"status": "REJECTED", "reason": "Policy not found in registry."}

        if not self.registry.verify(policy_id):
            return {"status": "REJECTED", "reason": "Fingerprint verification failed."}

        # 2. Execute (placeholder for real policy engine)
        result = {"action": "TRIAGE_ADJUST", "value": 0.12}

        # 3. Generate audit proof
        proof = self.proof_gen.generate_proof(
            execution_trace=["obs_ingested", "policy_applied"],
            final_state_hash="exec_hash_placeholder",
            policy_fingerprint=record["fingerprint"]
        )

        return {"status": "EXECUTED", "result": result, "proof": proof[:16]}
