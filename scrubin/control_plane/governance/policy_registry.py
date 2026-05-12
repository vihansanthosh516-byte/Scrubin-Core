from typing import Dict, Any, Optional
from scrubin.control_plane.governance.policy_signature import PolicySigner

class PolicyRegistry:
    """
    Immutable policy store. Once a policy is registered, it cannot be mutated.
    Provides retrieval by ID and fingerprint-based integrity checks.
    """
    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}

    def register(self, policy_id: str, policy_ir: Dict[str, Any],
                 compiler_version: str, seed: int) -> str:
        if policy_id in self._store:
            raise ValueError(f"Policy '{policy_id}' already registered. Mutation forbidden.")

        fingerprint = PolicySigner.generate_fingerprint(policy_ir, compiler_version, seed)
        self._store[policy_id] = {
            "ir": policy_ir,
            "compiler_version": compiler_version,
            "seed": seed,
            "fingerprint": fingerprint
        }
        return fingerprint

    def fetch(self, policy_id: str) -> Optional[Dict[str, Any]]:
        return self._store.get(policy_id)

    def verify(self, policy_id: str) -> bool:
        record = self._store.get(policy_id)
        if not record:
            return False
        return PolicySigner.verify(
            record["ir"], record["compiler_version"],
            record["seed"], record["fingerprint"]
        )
