from typing import Any
from scrubin.validation.ci_exports.stability_runner import run_stability_check

def run_calibration_gate(engine: Any, benchmark_registry: Any) -> bool:
    """
    ScrubIn Scientific Calibration Gate: The primary CI entry point.
    Returns ONLY boolean PASS/FAIL.
    """
    # 1. Run Stability Check (Sanitized)
    report = run_stability_check(engine, benchmark_registry)
    
    # 2. Evaluate Hard Thresholds
    # FAIL IF: any benchmark FAILED
    if report["status"] == "FAIL":
        return False
        
    # FAIL IF: global_stability_index < 0.90
    if report["global_stability_index"] < 0.90:
        return False
        
    # FAIL IF: any failed cases exist
    if report["failed_cases"]:
        return False
        
    return True
