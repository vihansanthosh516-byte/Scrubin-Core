from typing import Dict, Any, List
from scrubin.validation.suites.regression_suite import ScientificRegressionSuite
from scrubin.validation.ci_exports.regression_export import export_regression_results

def run_stability_check(engine: Any, benchmarks: Any) -> Dict[str, Any]:
    """
    CI Adapter Layer: Runs full scientific verification and outputs summary stats only.
    """
    # 1. Run the internal regression suite
    suite = ScientificRegressionSuite(engine)
    internal_results = suite.run_suite()
    
    # 2. Extract CI-safe metrics
    status = "PASS" if internal_results.passed else "FAIL"
    
    return {
        "status": status,
        "global_stability_index": round(1.0 - (sum(internal_results.scores.values()) / len(internal_results.scores)), 3),
        "worst_case": max(internal_results.scores, key=internal_results.scores.get) if internal_results.scores else None,
        "failed_cases": internal_results.failures,
        "summary": {
            "total_cases": len(internal_results.scores),
            "passed": len(internal_results.scores) - len(internal_results.failures),
            "failed": len(internal_results.failures)
        }
    }
