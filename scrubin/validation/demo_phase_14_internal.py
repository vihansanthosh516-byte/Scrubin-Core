from scrubin.control_plane.kernel import ControlPlaneKernel
from scrubin.validation.suites.regression_suite import ScientificRegressionSuite
from scrubin.validation.suites.population_suite import PopulationStabilitySuite
from scrubin.validation.stability.calibration_drift import CalibrationDriftEngine
from scrubin.validation.stability.longitudinal_tracker import LongitudinalTracker
from scrubin.validation.reports.drift_report import DriftReportGenerator

def run_phase_14_internal_demo():
    print("--- Phase 14: Internal Scientific Stability Core ---")
    
    # 1. Initialize Kernel and Systems
    kernel = ControlPlaneKernel(core_interface=None)
    regression_suite = ScientificRegressionSuite(kernel)
    pop_suite = PopulationStabilitySuite(kernel)
    drift_engine = CalibrationDriftEngine()
    tracker = LongitudinalTracker()
    
    # 2. Run Baseline Regression (Simulated Version 1.0)
    print("\n[Suite] Running Version 1.0 Clinical Regression...")
    v1_results = regression_suite.run_suite()
    print(f"  - Passed: {v1_results.passed}")
    print(f"  - Scores: {v1_results.scores}")
    
    for cid, score in v1_results.scores.items():
        tracker.add_record(cid, "v1.0", score)
        
    # 3. Run New Regression (Simulated Version 1.1 with minor drift)
    print("\n[Suite] Running Version 1.1 Clinical Regression...")
    v1_1_scores = {cid: score + 0.05 for cid, score in v1_results.scores.items()}
    # Update shock to have more drift
    v1_1_scores["ICU_SHOCK_001"] += 0.03
    
    for cid, score in v1_1_scores.items():
        tracker.add_record(cid, "v1.1", score)
        
    # 4. Compute Drift
    print("\n[Stability] Computing scientific calibration drift (v1.0 -> v1.1)...")
    drift = drift_engine.compute_drift(v1_results.scores, v1_1_scores)
    
    # 5. Population Stress Test
    print("\n[Population] Running synthetic patient distribution test...")
    pop_results = pop_suite.run_population_test(count=20)
    print(f"  - Avg Realism: {pop_results['average_realism']}")
    print(f"  - Outliers: {pop_results['outliers']}")
    
    # 6. Generate Drift Report
    print("\n" + DriftReportGenerator.generate(v1_results, drift))

    print("\n--- Phase 14 Internal Stability Demo Complete ---")

if __name__ == "__main__":
    run_phase_14_internal_demo()
