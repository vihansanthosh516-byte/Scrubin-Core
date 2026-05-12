from typing import Dict, Any, Optional
from scrubin.control_plane.schema_registry import SchemaRegistry
from scrubin.control_plane.contract_validator import ContractValidator

class RuntimeGuard:
    """
    Hard gate that blocks execution if contracts or schemas are violated.
    """
    def __init__(self, registry: SchemaRegistry, validator: ContractValidator):
        self.registry = registry
        self.validator = validator
        self.system_status = "HEALTHY"

    def allow_execution(self, job: Dict[str, Any], experiment: Dict[str, Any], world: Dict[str, Any]) -> bool:
        # 1. Schema Validation
        if not self.registry.validate("JobSchema", job):
            print(f"[GUARD] REJECTED: JobSchema validation failed for {job.get('job_id')}")
            return False

        # 2. Contract Validation
        contract_res = self.validator.validate_job(job, world)
        if not contract_res.valid:
            print(f"[GUARD] REJECTED: Contract violation: {', '.join(contract_res.violations)}")
            if contract_res.severity in ("HIGH", "CRITICAL"):
                return False

        # 3. Safety Kill Switch
        if self.system_status == "DEGRADED" and job.get("priority", 0) < 8:
            print(f"[GUARD] BLOCKED: Low priority job rejected during DEGRADED state.")
            return False

        return True

    def detect_drift(self, world_t: Dict[str, Any], world_prev: Dict[str, Any], threshold: float = 0.1):
        """
        Trigger emergency freeze if simulation drift exceeds threshold.
        """
        # Simplified drift check
        if abs(world_t.get("hash_seed", 0) - world_prev.get("hash_seed", 0)) > threshold:
            self.system_status = "DEGRADED"
            print("[GUARD] EMERGENCY: Significant state drift detected. Freezing non-critical jobs.")
