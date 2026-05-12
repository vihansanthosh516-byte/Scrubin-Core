import hashlib
import json
from typing import Dict, Any

class PolicySigner:
    """
    Cryptographic Policy Enforcement: Generates immutable fingerprints for clinical policies.
    Ensures that a policy can never silently change behavior after deployment.
    """
    @staticmethod
    def generate_fingerprint(policy_ir: Dict[str, Any], compiler_version: str, seed: int) -> str:
        # Canonical serialization to ensure stable hashing
        payload = {
            "ir": policy_ir,
            "compiler": compiler_version,
            "seed": seed
        }
        raw = json.dumps(payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    @staticmethod
    def verify(policy_ir: Dict[str, Any], compiler_version: str, seed: int, fingerprint: str) -> bool:
        return PolicySigner.generate_fingerprint(policy_ir, compiler_version, seed) == fingerprint
