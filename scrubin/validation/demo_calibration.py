from scrubin.control_plane.kernel import ControlPlaneKernel
from scrubin.control_plane.verification.gold_cases import GoldReplayCases
from scrubin.validation.validator import ScientificValidator

def run_phase_13_demo():
    print("--- Phase 13: Scientific Calibration Layer ---")
    
    # 1. Initialize Kernel and Validator
    kernel = ControlPlaneKernel(core_interface=None)
    validator = ScientificValidator()
    session_id = "scientific-sess-1"
    
    # 2. Run Reference Case (ICU Deterioration)
    print("\n[Simulation] Executing Gold Case 001 for scientific calibration...")
    GoldReplayCases.icu_deterioration_recovery(kernel, session_id)
    
    # 3. Perform Deterministic Replay
    print("[Replay] Reconstructing session state...")
    replay_result = kernel.replay.reconstruct_session(session_id)
    
    # 4. Run Scientific Validation
    print("\n[Calibration] Mapping simulation outputs to physiological models...")
    realism = validator.validate_session(replay_result)
    
    # 5. Output Calibration Report
    print("\n=== SCIENTIFIC CALIBRATION REPORT ===")
    print(f"Case ID: {session_id}")
    print(f"Realism Score: {realism.score} ({'PASS' if realism.score < 0.4 else 'NEEDS CALIBRATION'})")
    print("-" * 30)
    print(f"Physiological Distance (RMSE): {realism.physiological_distance:.3f}")
    print(f"Intervention Timing Error: {realism.timing_accuracy:.3f}")
    print(f"Outcome Alignment: {'MATCH' if realism.outcome_match else 'MISMATCH'}")
    
    if realism.score < 0.4:
        print("\nSTATUS: CLINICALLY PLAUSIBLE")
    else:
        print("\nSTATUS: SCIENTIFIC DIVERGENCE DETECTED")

    print("\n--- Phase 13 Scientific Calibration Demo Complete ---")

if __name__ == "__main__":
    run_phase_13_demo()
