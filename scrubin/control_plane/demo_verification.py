from scrubin.control_plane.kernel import ControlPlaneKernel
from scrubin.control_plane.verification.harness import DeterminismHarness
from scrubin.control_plane.verification.gold_cases import GoldReplayCases

def run_phase_12_8_demo():
    print("--- Phase 12.8: Determinism Verification Layer ---")
    
    # 1. Initialize Kernel and Verification Harness
    kernel = ControlPlaneKernel(core_interface=None)
    harness = DeterminismHarness(kernel)
    session_id = "gold-session-alpha"
    
    # 2. Run Gold Case Simulation
    print("\n[GoldCase] Executing canonical ICU deterioration/recovery trajectory...")
    GoldReplayCases.icu_deterioration_recovery(kernel, session_id)
    
    # 3. Bit-Identical Replay Test
    print("\n[Harness] Running Bit-Identical Replay Test (Test A)...")
    identical = harness.run_bit_identical_test(session_id)
    print(f"  - Result: {'PASSED' if identical else 'FAILED'}")
    
    # 4. CEG Consistency Test
    print("\n[Harness] Running CEG Causal Consistency Test (Test C)...")
    violations = harness.run_ceg_consistency_test(session_id)
    if not violations:
        print("  - Result: PASSED (All causal parents precede children)")
    else:
        for v in violations:
            print(f"  - VIOLATION: {v}")
            
    # 5. Order Invariance Stress Test
    print("\n[Harness] Running Event Ordering Invariance Test (Test B)...")
    # (Simulated shuffle of ingestion order)
    passed = harness.run_order_invariance_test(session_id)
    print(f"  - Result: {'PASSED' if passed else 'FAILED'}")
    
    # 6. Verify Final State
    result = kernel.replay.reconstruct_session(session_id)
    print(f"\n[Final Verification] Replay Output for {session_id}:")
    print(f"  - Final SpO2: {result['final_state'].vitals.get('spo2')}%")
    print(f"  - Execution Sequence: {result['execution_order']}")

    print("\n--- Phase 12.8 Determinism Verification Demo Complete ---")

if __name__ == "__main__":
    run_phase_12_8_demo()
