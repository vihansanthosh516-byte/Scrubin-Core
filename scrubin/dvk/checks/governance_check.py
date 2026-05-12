from scrubin.core_language.ces_validator import CESValidator
from scrubin.core_language.ces_spec import CESProgram

class GovernanceCheck:
    """Verifies: CES program fingerprint is stable and structurally valid."""
    def run(self, program: CESProgram, expected_fingerprint: str = "") -> bool:
        validator = CESValidator()
        if not validator.validate_program(program):
            return False
        if expected_fingerprint:
            actual = validator.compute_program_fingerprint(program)
            return actual == expected_fingerprint
        return True
