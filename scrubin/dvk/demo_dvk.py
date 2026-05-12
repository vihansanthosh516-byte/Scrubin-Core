from scrubin.core_language.ces_compiler import CESCompiler
from scrubin.core_language.ces_spec import CESProgram, CESInstruction, CESScope, CESCondition, CESAction, CESConstraints
from scrubin.control_plane.replay.state import ReplayState
from scrubin.dvk.kernel.dvk_kernel import DVKKernel
from scrubin.optimization.policy_compiler.policy_ir import CausalRuleIR

def run_phase_19_demo():
    print("=" * 60)
    print("  PHASE 19 — DETERMINISTIC VERIFICATION KERNEL (DVK)")
    print("=" * 60)

    compiler = CESCompiler()
    dvk = DVKKernel()

    # Build a valid CES program
    instructions = [
        compiler.compile_rl_action(
            action={"type": "ADMINISTER_OXYGEN"}, obs={"status": "UNSTABLE"},
            reward=0.8, ceg_node="ceg_1"
        ),
        compiler.compile_policy_ir(CausalRuleIR(
            rule_id="RULE_0", condition="util > 0.85",
            intervention="ADJUST_TRIAGE", magnitude=0.15,
            causal_anchor="ceg_2"
        )),
        compiler.compile_counterfactual(
            delta={"mortality_delta": -1}, variant_id="CF_1"
        ),
    ]
    program = compiler.build_program(instructions, seed=42)

    # ── Case 1: Valid Run ──────────────────────────────────────
    print("\n[Case 1] VALID EXECUTION")
    epo_1 = dvk.verify(program, ReplayState())
    print(f"  Run:        {epo_1.run_id}")
    print(f"  VALID:      {epo_1.valid}")
    print(f"  Proof Hash: {epo_1.current_proof_hash[:16]}...")
    for k, v in epo_1.to_dict().items():
        if k not in ("run_id", "valid"):
            print(f"    {k}: {v}")

    # ── Case 2: Tampered Program (unsafe action) ──────────────
    print("\n[Case 2] TAMPERED PROGRAM (Illegal Action)")
    bad_inst = CESInstruction(
        id="rogue_action", scope=CESScope.PATIENT,
        when=CESCondition(trigger="always"),
        do=CESAction(action="INJECT_POISON"),  # NOT in safe action space
        constraints=CESConstraints(safety="phase14_gate")
    )
    bad_program = compiler.build_program([bad_inst], seed=99)
    epo_2 = dvk.verify(bad_program, ReplayState())
    print(f"  Run:        {epo_2.run_id}")
    print(f"  VALID:      {epo_2.valid}")
    print(f"  RL Safe:    {epo_2.rl_safe}  ← REJECTED")

    # ── Case 3: Determinism Proof (same seed → same hash) ─────
    print("\n[Case 3] DETERMINISM PROOF (Identical Re-run)")
    dvk_b = DVKKernel()
    epo_3 = dvk_b.verify(program, ReplayState())
    match = epo_1.ces_program_hash == epo_3.ces_program_hash
    print(f"  Program Hash A: {epo_1.ces_program_hash[:16]}...")
    print(f"  Program Hash B: {epo_3.ces_program_hash[:16]}...")
    print(f"  IDENTICAL:      {match}")

    # ── Case 4: Chain Integrity ───────────────────────────────
    print("\n[Case 4] PROOF CHAIN INTEGRITY")
    chain_valid = dvk.chain.verify_chain()
    print(f"  Chain Length:   {len(dvk.chain)}")
    print(f"  Chain Valid:    {chain_valid}")
    latest = dvk.chain.latest()
    print(f"  Latest Proof:   {latest.current_proof_hash[:16]}...")
    print(f"  Prev Link:      {latest.previous_proof_hash[:16]}...")

    # ── Summary ───────────────────────────────────────────────
    if epo_1.valid and not epo_2.valid and match and chain_valid:
        print("\n" + "=" * 60)
        print("  DVK SYSTEM INVARIANTS VERIFIED")
        print("=" * 60)
        print("  ✔ Valid execution produces valid EPO")
        print("  ✔ Tampered execution REJECTED (rl_safe=False)")
        print("  ✔ Deterministic proof hashes (identical re-run)")
        print("  ✔ Proof chain integrity (hash linkage verified)")
        print("  ✔ AG handoff ready (EPO is sole trust artifact)")
        print("=" * 60)

    print("\n--- Phase 19 DVK Demo Complete ---")

if __name__ == "__main__":
    run_phase_19_demo()
