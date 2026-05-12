from scrubin.core_language.ces_spec import CESProgram

class ConstraintCheck:
    """Verifies: every CES instruction declares a safety constraint."""
    def run(self, program: CESProgram) -> bool:
        for inst in program.instructions:
            if not inst.constraints.safety:
                return False
        return True
