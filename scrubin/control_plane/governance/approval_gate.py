from typing import Dict, Any

class ApprovalGate:
    """
    Pre-deployment validation gate.
    Blocks deployment unless all prior phase invariants are satisfied.
    """
    def evaluate(self, report: Dict[str, Any]) -> bool:
        checks = {
            "determinism_pass": report.get("determinism_pass", False),
            "calibration_stable": report.get("calibration_stable", False),
            "rl_safety_valid": report.get("rl_safety_valid", False),
            "counterfactual_stable": report.get("counterfactual_stable", False),
        }

        failures = [k for k, v in checks.items() if not v]
        if failures:
            print(f"[APPROVAL GATE] BLOCKED — Failed checks: {failures}")
            return False

        print("[APPROVAL GATE] ALL CHECKS PASSED — Deployment approved.")
        return True
