import hashlib, json
from typing import List, Dict, Any
from scrubin.core_language.ces_spec import CESProgram

class TraceNormalizer:
    """
    Converts CES execution output into a canonical, hash-stable trace representation.
    """
    def normalize(self, program: CESProgram, execution_log: List[Dict[str, Any]]) -> str:
        canonical = {
            "program_id": program.program_id,
            "seed": program.seed,
            "instruction_ids": [i.id for i in program.instructions],
            "execution_log": execution_log
        }
        raw = json.dumps(canonical, sort_keys=True).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

class DVKCompiler:
    """
    Transforms a normalized CES trace + check results into an ExecutionProofObject.
    """
    def compile_proof_hashes(self, program: CESProgram, state_before: Any,
                              state_after: Any, execution_log: List) -> Dict[str, str]:
        normalizer = TraceNormalizer()
        trace_hash = normalizer.normalize(program, execution_log)

        program_hash = hashlib.sha256(
            json.dumps([i.id for i in program.instructions], sort_keys=True).encode()
        ).hexdigest()

        init_hash = hashlib.sha256(str(state_before).encode()).hexdigest()
        final_hash = hashlib.sha256(str(state_after).encode()).hexdigest()

        return {
            "ces_program_hash": program_hash,
            "initial_state_hash": init_hash,
            "final_state_hash": final_hash,
            "execution_trace_hash": trace_hash
        }
