from dataclasses import dataclass
from typing import Dict, Any, List

@dataclass
class BenchmarkCase:
    id: str
    name: str
    clinical_scenario: str
    reference_trajectory: Dict[str, Any]
    expected_ranges: Dict[str, Any]
    intervention_expectations: Dict[str, Any]
    outcome_expectation: Dict[str, Any]

class BenchmarkRegistry:
    """
    Centralized catalog of clinical ground truth for simulation anchoring.
    """
    def __init__(self):
        self.benchmarks: Dict[str, BenchmarkCase] = {}
        self._load_standard_benchmarks()

    def _load_standard_benchmarks(self):
        self.register(BenchmarkCase(
            id="ICU_SEPSIS_001",
            name="Early Sepsis Progression",
            clinical_scenario="Patient presenting with fever, tachycardia, and early hypoxia.",
            reference_trajectory={"spo2": [98, 92, 85], "hr": [80, 110, 130]},
            expected_ranges={"hr": [70, 150], "spo2": [70, 100]},
            intervention_expectations={"FLUID_BOLUS": {"timing": "early"}},
            outcome_expectation={"survival": True}
        ))
        
        self.register(BenchmarkCase(
            id="ICU_HYPOXIA_001",
            name="Acute Respiratory Failure",
            clinical_scenario="Sudden SpO2 drop following trauma.",
            reference_trajectory={"spo2": [98, 85, 75], "hr": [80, 100, 120]},
            expected_ranges={"spo2": [60, 100]},
            intervention_expectations={"O2_THERAPY": {"timing": "urgent"}},
            outcome_expectation={"survival": True}
        ))
        
        self.register(BenchmarkCase(
            id="ICU_SHOCK_001",
            name="Hypovolemic Shock",
            clinical_scenario="Rapid blood loss with decompensating vitals.",
            reference_trajectory={"hr": [80, 130, 160]},
            expected_ranges={"hr": [60, 200]},
            intervention_expectations={"TRANSFUSION": {"timing": "immediate"}},
            outcome_expectation={"survival": False} # High mortality risk
        ))

    def register(self, case: BenchmarkCase):
        self.benchmarks[case.id] = case

    def get(self, case_id: str) -> BenchmarkCase:
        return self.benchmarks[case_id]
