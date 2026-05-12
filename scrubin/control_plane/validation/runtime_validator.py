from typing import Dict, Any, List
from scrubin.control_plane.schema_registry import SchemaRegistry
from scrubin.control_plane.contract_validator import ContractValidator
from scrubin.control_plane.runtime_guard import RuntimeGuard
from scrubin.control_plane.diffcheck import DiffChecker

class RuntimeVerificationLayer:
    """
    Orchestrates the full validation pipeline: Schema -> Contract -> Guard -> DiffCheck.
    """
    def __init__(self):
        self.registry = SchemaRegistry()
        self.contract_validator = ContractValidator()
        self.guard = RuntimeGuard(self.registry, self.contract_validator)
        self.diffcheck = DiffChecker()

    def validate_execution_intent(self, job: Dict[str, Any], experiment: Dict[str, Any], world: Dict[str, Any]) -> bool:
        """
        Final hard-gate before simulation core execution.
        """
        # Step 1 & 2 & 3: Runtime Guard handles Schema + Contract + System Health
        return self.guard.allow_execution(job, experiment, world)

    def verify_state_transition(self, world_t: Dict[str, Any], world_prev: Dict[str, Any]) -> bool:
        """
        Post-execution verification.
        """
        report = self.diffcheck.compare_worlds(world_t, world_prev)
        if report.divergence_score > 2.0:
            print(f"[VERIFIER] CRITICAL: Post-execution divergence high ({report.divergence_score})")
            return False
        return True
