from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class HospitalPolicy:
    name: str
    triage_threshold: float = 0.5
    icu_expansion_limit: int = 10
    staff_allocation_strategy: str = "critical_first"

class GovernanceEngine:
    """
    Manages and evolves hospital-level policies.
    """
    def __init__(self):
        self.current_policy = HospitalPolicy("Standard Operating Procedure")
        self.policy_history: List[HospitalPolicy] = []

    def adapt_policy(self, hospital_load: float):
        """
        Adjust policies based on hospital stress.
        """
        if hospital_load > 0.9:
            # Shift to Crisis Standards of Care
            self.current_policy.triage_threshold = 0.7
            self.current_policy.icu_expansion_limit = 20
            self.current_policy.staff_allocation_strategy = "survival_maximization"
        elif hospital_load < 0.6:
            # Return to normal
            self.current_policy.triage_threshold = 0.5
            self.current_policy.icu_expansion_limit = 10
            self.current_policy.staff_allocation_strategy = "standard_care"

    def get_policy_dict(self) -> Dict[str, Any]:
        return {
            "name": self.current_policy.name,
            "triage_threshold": self.current_policy.triage_threshold,
            "icu_expansion_limit": self.current_policy.icu_expansion_limit,
            "staff_allocation_strategy": self.current_policy.staff_allocation_strategy
        }
