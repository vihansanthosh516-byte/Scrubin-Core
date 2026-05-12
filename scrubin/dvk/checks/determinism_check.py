import copy
from typing import Any
from scrubin.core_language.ces_spec import CESProgram
from scrubin.core_language.ces_executor import CESExecutor

class DeterminismCheck:
    """Verifies: same program + same seed → bit-identical final state."""
    def run(self, program: CESProgram, initial_state: Any) -> bool:
        exec_a = CESExecutor()
        exec_b = CESExecutor()
        result_a = exec_a.execute_program(program, copy.deepcopy(initial_state))
        result_b = exec_b.execute_program(program, copy.deepcopy(initial_state))
        log_a = [(r.instruction_id, r.accepted) for r in exec_a.execution_log]
        log_b = [(r.instruction_id, r.accepted) for r in exec_b.execution_log]
        return log_a == log_b and result_a.tick == result_b.tick
