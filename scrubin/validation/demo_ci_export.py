from scrubin.control_plane.kernel import ControlPlaneKernel
from scrubin.validation.ci_exports.calibration_gate import run_calibration_gate
from scrubin.validation.ci_exports.stability_runner import run_stability_check

def run_ci_export_demo():
    print("--- Phase 14 Step 2: CI Export Layer (Scientific Enforcement) ---")
    
    # 1. Initialize Kernel
    kernel = ControlPlaneKernel(core_interface=None)
    
    # 2. Run CI Stability Runner (Sanitized Output)
    print("\n[CI Runner] Executing sanitized stability check...")
    ci_report = run_stability_check(kernel, None)
    print(f"  - Status: {ci_report['status']}")
    print(f"  - Stability Index: {ci_report['global_stability_index']}")
    print(f"  - Worst Case: {ci_report['worst_case']}")
    print(f"  - Summary: {ci_report['summary']}")
    
    # 3. Test Calibration Gate (True/False only)
    print("\n[CI Gate] Running deterministic calibration gate...")
    passed = run_calibration_gate(kernel, None)
    print(f"  - Result: {'PASSED (Green Light)' if passed else 'FAILED (Blocked)'}")
    
    # 4. Invariant Verification: No Semantic Leakage
    print("\n[Invariant Check] Verifying zero semantic leakage to CI...")
    leakage = [k for k in ci_report if k in ["vitals", "trajectories", "ceg"]]
    if not leakage:
        print("  - SUCCESS: No internal clinical state leaked to CI layer.")
    else:
        print(f"  - FAILED: Leaked keys found: {leakage}")

    print("\n--- Phase 14 CI Export Layer Demo Complete ---")

if __name__ == "__main__":
    run_ci_export_demo()
