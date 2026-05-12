from typing import List

class ClinicalAction:
    def __init__(self, action_type: str, target: str = "global", value: float = 1.0):
        self.type = action_type
        self.target = target
        self.value = value

ACTIONS = [
    "ADMINISTER_OXYGEN",
    "INTUBATE",
    "FLUID_BOLUS",
    "VASOPRESSOR",
    "OBSERVE",
    "DIAGNOSTIC_ORDER"
]
