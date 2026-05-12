from typing import List, Dict, Any

def export_regression_results(results: Any) -> Dict[str, Any]:
    """
    Normalizes internal regression results into a flattened CI-readable format.
    """
    failures = []
    # If the results object has failures (case IDs)
    for cid in getattr(results, "failures", []):
        failures.append({
            "case_id": cid,
            "reason": "clinical realism threshold exceeded",
            "drift": getattr(results, "scores", {}).get(cid, 1.0)
        })
        
    return {
        "failures": failures,
        "summary": {
            "global_drift": sum(getattr(results, "scores", {}).values()) / len(getattr(results, "scores", {})) if getattr(results, "scores", {}) else 0.0
        }
    }
