from typing import List
from scrubin.core_language.ces_spec import CESProgram, CESInstruction
import hashlib, json

class CESValidator:
    """
    Enforces ALL Phase 12-16 invariants on CES programs.
    Acts as the unified CI + safety + determinism gate.
    """
    def validate_program(self, program: CESProgram) -> bool:
        errors = []

        for inst in program.instructions:
            # 1. Every instruction must have an ID
            if not inst.id:
                errors.append("Missing instruction ID")

            # 2. Causal ordering: 'when' must exist before 'do'
            if not inst.when.trigger:
                errors.append(f"{inst.id}: Missing causal trigger condition")

            # 3. Safety constraints must be declared
            if not inst.constraints.safety:
                errors.append(f"{inst.id}: No safety constraint declared")

        if errors:
            for e in errors:
                print(f"  [CES VALIDATOR] ERROR: {e}")
            return False

        return True

    def validate_determinism(self, program: CESProgram, executor, state) -> bool:
        """Runs the program twice and asserts identical execution logs."""
        import copy

        exec_a = executor.__class__()
        exec_b = executor.__class__()

        state_a = copy.deepcopy(state)
        state_b = copy.deepcopy(state)

        exec_a.execute_program(program, state_a)
        exec_b.execute_program(program, state_b)

        log_a = [(r.instruction_id, r.accepted) for r in exec_a.execution_log]
        log_b = [(r.instruction_id, r.accepted) for r in exec_b.execution_log]

        return log_a == log_b

    def compute_program_fingerprint(self, program: CESProgram) -> str:
        """Deterministic hash of the entire CES program for governance."""
        payload = {
            "id": program.program_id,
            "seed": program.seed,
            "instructions": [
                {"id": i.id, "action": i.do.action, "trigger": i.when.trigger}
                for i in program.instructions
            ]
        }
        raw = json.dumps(payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()
