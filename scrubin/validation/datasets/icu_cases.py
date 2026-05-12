from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class ICUTrajectory:
    case_id: str
    vitals_history: List[Dict[str, Any]]
    interventions: List[Dict[str, Any]]
    expected_outcome: str

class ICUDataset:
    """
    Gold reference truth trajectories for clinical calibration.
    """
    @staticmethod
    def sepsis_case_01() -> ICUTrajectory:
        return ICUTrajectory(
            case_id="SEPSIS_01",
            vitals_history=[
                {"tick": 0, "hr": 80, "spo2": 98},
                {"tick": 100, "hr": 110, "spo2": 92},
                {"tick": 200, "hr": 130, "spo2": 85}
            ],
            interventions=[
                {"tick": 110, "action": "FLUID_BOLUS"}
            ],
            expected_outcome="SURVIVED"
        )
