from dataclasses import dataclass, field
from typing import List, Dict, Any, Literal, Optional

@dataclass
class ValidationResult:
    valid: bool
    violations: List[str] = field(default_factory=list)
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "LOW"

class ContractValidator:
    """
    Validates semantic relationships and invariants across system boundaries.
    """
    def validate_experiment(self, exp: Dict[str, Any]) -> ValidationResult:
        violations = []
        severity = "LOW"
        
        # Rule: Determinism Contract
        if exp.get("config", {}).get("deterministic") is True:
            if "random_seed" not in exp.get("config", {}):
                violations.append("Determinism requested but no random_seed provided.")
                severity = "HIGH"

        return ValidationResult(len(violations) == 0, violations, severity)

    def validate_job(self, job: Dict[str, Any], world: Dict[str, Any]) -> ValidationResult:
        violations = []
        severity = "LOW"
        
        job_type = job.get("job_type")
        payload = job.get("payload", {})
        
        # Rule: MCTS Contract
        if job_type == "VECTOR_BATCH":
            if payload.get("max_depth", 0) > 10:
                violations.append("VECTOR_BATCH max_depth cannot exceed 10 for performance safety.")
                severity = "MEDIUM"

        # Rule: Resource Contract
        resources = world.get("resources", {})
        if resources.get("ventilators_used", 0) > resources.get("ventilators_available", 0):
            violations.append("Resource safety violation: Ventilator demand exceeds capacity.")
            severity = "CRITICAL"

        return ValidationResult(len(violations) == 0, violations, severity)

    def validate_snapshot(self, snapshot: Dict[str, Any], prev_snapshot: Optional[Dict[str, Any]]) -> ValidationResult:
        violations = []
        severity = "LOW"
        
        if prev_snapshot:
            # Rule: Snapshot Continuity Contract
            if snapshot.get("tick", 0) <= prev_snapshot.get("tick", 0):
                violations.append("Snapshot tick must be strictly greater than previous snapshot.")
                severity = "HIGH"
                
        return ValidationResult(len(violations) == 0, violations, severity)
