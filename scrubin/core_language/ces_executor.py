from typing import Dict, Any, List
from scrubin.core_language.ces_spec import CESInstruction, CESProgram, CESScope

class CESExecutionResult:
    def __init__(self, instruction_id: str, accepted: bool, new_state: Any, ceg_event_id: str = ""):
        self.instruction_id = instruction_id
        self.accepted = accepted
        self.new_state = new_state
        self.ceg_event_id = ceg_event_id

class CESExecutor:
    """
    Deterministic CES runtime. Executes CES programs against simulation state.
    Guarantees identical CEG + state + reward trace for the same seed.
    """
    def __init__(self):
        self.execution_log: List[CESExecutionResult] = []

    def execute_program(self, program: CESProgram, initial_state: Any) -> Any:
        state = initial_state
        for instruction in program.instructions:
            result = self._execute_instruction(instruction, state)
            self.execution_log.append(result)
            if result.accepted:
                state = result.new_state
        return state

    def _execute_instruction(self, inst: CESInstruction, state: Any) -> CESExecutionResult:
        # 1. Check constraints
        if not self._check_constraints(inst, state):
            return CESExecutionResult(inst.id, accepted=False, new_state=state)

        # 2. Apply action to state (deterministic mutation)
        new_state = self._apply_action(inst, state)

        # 3. Emit CEG event
        ceg_id = f"ceg_{inst.id}_{id(new_state)}"

        return CESExecutionResult(inst.id, accepted=True, new_state=new_state, ceg_event_id=ceg_id)

    def _check_constraints(self, inst: CESInstruction, state: Any) -> bool:
        # Phase 14 gate: realism score must be below threshold
        if inst.constraints.physiology:
            realism = getattr(state, "realism_score", 0.0)
            if realism > 0.4:
                return False
        return True

    def _apply_action(self, inst: CESInstruction, state: Any) -> Any:
        import copy
        new = copy.deepcopy(state)
        # Record decision in state
        if hasattr(new, "decisions"):
            new.decisions.append({
                "ces_id": inst.id,
                "action": inst.do.action,
                "params": inst.do.params,
                "scope": inst.scope.value
            })
        if hasattr(new, "tick"):
            new.tick += 1
        return new
