import copy, hashlib
from typing import Any
from scrubin.core_language.ces_spec import CESProgram
from scrubin.core_language.ces_executor import CESExecutor

class ReplayEquivalenceCheck:
    """Verifies: replay of execution produces bit-identical final state hash."""
    def run(self, program: CESProgram, initial_state: Any) -> bool:
        exec_a = CESExecutor()
        exec_b = CESExecutor()
        result_a = exec_a.execute_program(program, copy.deepcopy(initial_state))
        result_b = exec_b.execute_program(program, copy.deepcopy(initial_state))
        hash_a = hashlib.sha256(str(result_a).encode()).hexdigest()
        hash_b = hashlib.sha256(str(result_b).encode()).hexdigest()
        return hash_a == hash_b
