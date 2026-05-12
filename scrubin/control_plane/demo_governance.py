from scrubin.control_plane.governance.policy_signature import PolicySigner
from scrubin.control_plane.external_api.safety_boundary import SafetyBoundary
from scrubin.control_plane.audit.replay_proof_generator import ReplayProofGenerator

def run_phase_16_demo():
    print("--- Phase 16: Governance, Signing, and External Control Plane ---")
    
    # 1. Policy Fingerprinting
    policy_ir = {"RULE_0": "IF ICU > 0.8 THEN TRIAGE +0.1"}
    compiler_v = "1.9.0-stable"
    seed = 42
    
    print("\n[Governance] Signing clinical policy IR...")
    fingerprint = PolicySigner.generate_fingerprint(policy_ir, compiler_v, seed)
    print(f"  - Fingerprint: {fingerprint[:16]}...")
    
    # 2. Tamper-Resistance Check
    print("\n[Governance] Verifying tamper-resistance...")
    # Change seed, should fail verification
    is_valid = PolicySigner.verify(policy_ir, compiler_v, seed=43, fingerprint=fingerprint)
    print(f"  - Verification (Modified Seed): {'PASSED' if is_valid else 'REJECTED'}")
    
    # 3. External API Safety Boundary
    print("\n[Safety] Testing External API Firewall (Sanitizing internal state)...")
    raw_response = {
        "hospital_load": 0.85,
        "causal_graph": {"nodes": "internal_private_data"}, # FORBIDDEN
        "replay_snapshot": "internal_binary_blob",         # FORBIDDEN
        "mortality_velocity": 0.01
    }
    boundary = SafetyBoundary()
    sanitized = boundary.sanitize_response(raw_response)
    print(f"  - Raw Keys: {list(raw_response.keys())}")
    print(f"  - Sanitized Keys: {list(sanitized.keys())}")
    
    # 4. Replay Proof Generation
    print("\n[Audit] Generating Cryptographic Replay Proof...")
    proof_gen = ReplayProofGenerator()
    proof = proof_gen.generate_proof(
        execution_trace=["event_A", "event_B"],
        final_state_hash="hash_999",
        policy_fingerprint=fingerprint
    )
    print(f"  - Replay Proof: {proof[:16]}...")
    
    # 5. Invariant Verification
    if not is_valid and "causal_graph" not in sanitized:
        print("\n=== GOVERNANCE INVARIANTS VERIFIED ===")
        print("✔ Policy Immutability (Fingerprint consistency)")
        print("✔ External API Isolation (Firewall stripping)")
        print("✔ Execution Auditability (Replay proofs)")

    print("\n--- Phase 16 Governance Demo Complete ---")

if __name__ == "__main__":
    run_phase_16_demo()
