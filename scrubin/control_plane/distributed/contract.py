from typing import Dict, Any, List
from scrubin.control_plane.contract_validator import ContractValidator, ValidationResult

class DistributedContractValidator(ContractValidator):
    """
    Extends formal contracts into the distributed domain (multi-node aware).
    """
    def validate_cluster_resources(self, assignments: Dict[str, List[str]], global_resources: Dict[str, Any]) -> ValidationResult:
        violations = []
        severity = "LOW"
        
        # Rule: Global ICU capacity across all nodes
        total_assigned_patients = sum(len(ids) for ids in assignments.values())
        max_capacity = global_resources.get("total_beds", 1000)
        
        if total_assigned_patients > max_capacity:
            violations.append(f"Cluster-wide capacity exceeded: {total_assigned_patients}/{max_capacity}")
            severity = "CRITICAL"
            
        # Rule: Cross-node resource locking
        # In a real system, we'd check for multi-node lock contention
            
        return ValidationResult(len(violations) == 0, violations, severity)

    def validate_node_assignment(self, node_id: str, job_type: str, node_capabilities: Dict[str, Any]) -> bool:
        """
        Ensures a node has the required specialization for a job.
        """
        if job_type not in node_capabilities.get("supported_job_types", []):
            return False
        return True
