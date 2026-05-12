import copy, hashlib
from typing import Any, Dict, Optional
from scrubin.core_language.ces_spec import CESProgram
from scrubin.core_language.ces_executor import CESExecutor
from scrubin.dvk.kernel.proof_object import ExecutionProofObject, compute_epo_hash
from scrubin.dvk.kernel.proof_chain import ProofChain
from scrubin.dvk.compiler.dvk_compiler import DVKCompiler
from scrubin.dvk.checks.determinism_check import DeterminismCheck
from scrubin.dvk.checks.causal_check import CausalCheck
from scrubin.dvk.checks.constraint_check import ConstraintCheck
from scrubin.dvk.checks.governance_check import GovernanceCheck
from scrubin.dvk.checks.rl_safety_check import RLSafetyCheck
from scrubin.dvk.checks.replay_equivalence_check import ReplayEquivalenceCheck

class DVKKernel:
    """
    Deterministic Verification Kernel.
    Single entrypoint that transforms CES execution into a cryptographically
    verifiable ExecutionProofObject. AG trusts this as the final authority.
    """
    def __init__(self):
        self.chain = ProofChain()
        self.compiler = DVKCompiler()
        self._run_counter = 0

    def verify(self, program: CESProgram, initial_state: Any,
               policy_fingerprint: str = "",
               counterfactual_hash: str = "") -> ExecutionProofObject:
        """
        Full DVK verification pipeline:
        1. Execute CES program
        2. Run all invariant checks
        3. Compute hashes
        4. Build EPO
        5. Append to proof chain
        """
        self._run_counter += 1
        run_id = f"dvk_run_{self._run_counter}"

        # 1. Execute
        executor = CESExecutor()
        state_before = copy.deepcopy(initial_state)
        final_state = executor.execute_program(program, copy.deepcopy(initial_state))
        exec_log = [(r.instruction_id, r.accepted) for r in executor.execution_log]

        # 2. Compute hashes
        hashes = self.compiler.compile_proof_hashes(
            program, state_before, final_state, exec_log
        )

        # 3. Run invariant checks
        det = DeterminismCheck().run(program, initial_state)
        causal = CausalCheck().run(program)
        constraints = ConstraintCheck().run(program)
        governance = GovernanceCheck().run(program)
        rl_safe = RLSafetyCheck().run(program)
        replay = ReplayEquivalenceCheck().run(program, initial_state)

        # 4. Build proof hash
        prev_hash = self.chain.latest().current_proof_hash if self.chain.latest() else "GENESIS"
        causal_graph_hash = hashlib.sha256("ceg_placeholder".encode()).hexdigest()

        current_hash = compute_epo_hash(
            run_id, hashes["ces_program_hash"],
            hashes["final_state_hash"], hashes["execution_trace_hash"],
            prev_hash
        )

        # 5. Construct EPO
        epo = ExecutionProofObject(
            run_id=run_id,
            ces_program_hash=hashes["ces_program_hash"],
            initial_state_hash=hashes["initial_state_hash"],
            final_state_hash=hashes["final_state_hash"],
            causal_graph_hash=causal_graph_hash,
            determinism_verified=det,
            replay_equivalent=replay,
            constraint_satisfied=constraints,
            governance_valid=governance,
            rl_safe=rl_safe,
            counterfactual_consistency_hash=counterfactual_hash or "N/A",
            global_policy_fingerprint=policy_fingerprint or "N/A",
            execution_trace_hash=hashes["execution_trace_hash"],
            previous_proof_hash=prev_hash,
            current_proof_hash=current_hash
        )

        # 6. Append to chain
        self.chain.append(epo)

        return epo
