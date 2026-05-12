"""
CI Gate 1: Policy Fingerprint Integrity
Verifies that deployed policies hash identically across environments.
"""
import sys
sys.path.insert(0, ".")

from scrubin.control_plane.governance.policy_signature import PolicySigner

def run_gate():
    policy_ir = {"RULE_0": "IF ICU > 0.8 THEN TRIAGE +0.1"}
    compiler_v = "1.9.0-stable"
    seed = 42

    fp1 = PolicySigner.generate_fingerprint(policy_ir, compiler_v, seed)
    fp2 = PolicySigner.generate_fingerprint(policy_ir, compiler_v, seed)

    assert fp1 == fp2, "FAIL: Policy fingerprint is non-deterministic."

    # Tamper detection
    tampered_ir = {"RULE_0": "IF ICU > 0.8 THEN TRIAGE +0.2"}
    assert not PolicySigner.verify(tampered_ir, compiler_v, seed, fp1), \
        "FAIL: Tampered policy passed verification."

    print("[GATE 1] PASS — Policy fingerprint integrity verified.")

if __name__ == "__main__":
    run_gate()
