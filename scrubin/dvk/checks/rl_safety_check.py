from scrubin.core_language.ces_spec import CESProgram

SAFE_ACTIONS = {
    "ADMINISTER_OXYGEN", "INTUBATE", "FLUID_BOLUS", "VASOPRESSOR",
    "OBSERVE", "DIAGNOSTIC_ORDER", "ADJUST_TRIAGE", "SYSTEM_INTERVENTION",
    "POLICY_VARIANT"
}

class RLSafetyCheck:
    """Verifies: all CES actions fall within the constrained clinical action space."""
    def run(self, program: CESProgram) -> bool:
        for inst in program.instructions:
            if inst.do.action not in SAFE_ACTIONS:
                return False
        return True
