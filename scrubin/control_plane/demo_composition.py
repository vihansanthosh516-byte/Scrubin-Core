from scrubin.control_plane.kernel import ControlPlaneKernel
from scrubin.control_plane.verification.gold_cases import GoldReplayCases
from scrubin.control_plane.scenarios.adversarial_profiles import AdversarialProfiles
from scrubin.control_plane.stress.composition_runner import CompositionStressRunner

def run_phase_12_9_1_demo():
    print("--- Phase 12.9.1: Adversarial Composition Stress Layer ---")
    
    # 1. Initialize Kernel and Runner
    kernel = ControlPlaneKernel(core_interface=None)
    runner = CompositionStressRunner(kernel)
    session_id = "comp-sess-1"
    
    # 2. Setup Baseline Gold Case
    print("\n[Baseline] Establishing canonical ICU trajectory...")
    GoldReplayCases.icu_deterioration_recovery(kernel, session_id)
    
    # 3. Test: Burst Chaos Profile (Composed Mutators)
    print("\n[Profile: Burst Chaos] Testing stability under high-frequency duplication + shuffle...")
    result_burst = runner.run_composition_test(
        session_id, 
        AdversarialProfiles.burst_chaos(), 
        depth=2
    )
    print(f"  - Depth: {result_burst['depth']}")
    print(f"  - Deterministic: {'PASSED' if result_burst['deterministic'] else 'FAILED'}")
    
    # 4. Test: Cascading Failure Profile (Recursive Layering)
    print("\n[Profile: Cascading Failure] Testing deep recursive delay layering (Depth 5)...")
    result_cascade = runner.run_composition_test(
        session_id, 
        AdversarialProfiles.cascading_failure(), 
        depth=5
    )
    print(f"  - Depth: {result_cascade['depth']}")
    print(f"  - Deterministic: {'PASSED' if result_cascade['deterministic'] else 'FAILED'}")
    
    # 5. Analysis: Maximum Entropy Interaction
    print("\n[Analysis] Testing combinatorial maximum entropy (All mutators interacting)...")
    result_entropy = runner.run_composition_test(
        session_id, 
        AdversarialProfiles.maximum_entropy(), 
        depth=3
    )
    print(f"  - Result Hash: {result_entropy['replay_hash'][:12]}...")
    print(f"  - Baseline Hash: {result_entropy['baseline_hash'][:12]}...")
    
    if result_entropy['deterministic']:
        print("\n=== COMPOSITION STRESS REPORT ===")
        print("STATUS: PASSED")
        print("RESULT: System survived interacting multi-layer chaos injection.")
    else:
        print("\n=== COMPOSITION STRESS REPORT ===")
        print("STATUS: FAILED")
        print("RESULT: Combinatorial failure detected in layered mutation pipeline.")

    print("\n--- Phase 12.9.1 Adversarial Composition Demo Complete ---")

if __name__ == "__main__":
    run_phase_12_9_1_demo()
