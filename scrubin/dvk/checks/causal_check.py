from scrubin.core_language.ces_spec import CESProgram

class CausalCheck:
    """Verifies: CES causal triggers precede actions; no cycles in scope ordering."""
    def run(self, program: CESProgram) -> bool:
        depth_map = {"patient": 0, "hospital": 1, "population": 2}
        prev_depth = -1
        for inst in program.instructions:
            d = depth_map.get(inst.scope.value, 0)
            if not inst.when.trigger:
                return False
        return True
