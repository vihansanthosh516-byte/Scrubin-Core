from dataclasses import dataclass, field
from scrubin.decision.planning import PlanningState

@dataclass
class FutureOutcome:
    name: str
    probability: float
    description: str

@dataclass
class FutureBranch:
    action_name: str
    outcomes: list[FutureOutcome]
    expected_utility: float

@dataclass
class FutureTrajectory:
    root_tick: int
    branches: list[FutureBranch] = field(default_factory=list)
    optimal_path: list[str] = field(default_factory=list)
    
class FutureSimulator:
    @staticmethod
    def generate_branches(action_name: str) -> FutureBranch:
        """
        Creates probabilistic outcomes for interventions.
        """
        if action_name == "intubation":
            return FutureBranch(
                action_name=action_name,
                expected_utility=0.0,
                outcomes=[
                    FutureOutcome("stabilization", 0.72, "Immediate improvement in oxygenation"),
                    FutureOutcome("prolonged_dependency", 0.18, "Requires extended ICU ventilator support"),
                    FutureOutcome("deterioration", 0.10, "Post-intubation hypotension and crash")
                ]
            )
        elif action_name == "vasopressors":
            return FutureBranch(
                action_name=action_name,
                expected_utility=0.0,
                outcomes=[
                    FutureOutcome("bp_recovery", 0.61, "Stabilization of MAP"),
                    FutureOutcome("arrhythmia", 0.22, "Tachycardic complications"),
                    FutureOutcome("organ_ischemia", 0.17, "Peripheral and renal damage")
                ]
            )
        else:
            return FutureBranch(
                action_name=action_name,
                expected_utility=0.0,
                outcomes=[FutureOutcome("standard_effect", 1.0, "Expected outcome")]
            )
