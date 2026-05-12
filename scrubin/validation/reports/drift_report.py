from typing import Any, Dict
from scrubin.validation.stability.calibration_drift import DriftResult

class DriftReportGenerator:
    """
    Produces human-readable scientific stability summaries.
    """
    @staticmethod
    def generate(result: Any, drift: DriftResult) -> str:
        report = []
        report.append("=== PHASE 14 DRIFT REPORT ===")
        report.append(f"\nGlobal Stability Index: {round(1.0 - drift.global_drift, 3)}")
        report.append(f"\nWorst Case:")
        report.append(f" - {drift.worst_case}")
        report.append(f" - Drift: {round(drift.per_case_drift.get(drift.worst_case or '', 0.0), 3)}")
        
        status = "ACCEPTABLE" if drift.global_drift < 0.1 else "MONITORED"
        if drift.global_drift > 0.2: status = "CRITICAL REGRESSION"
        
        report.append(f"\nStatus: {status}")
        return "\n".join(report)
