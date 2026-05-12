import copy
from scrubin.core_language.ces_compiler import CESCompiler
from scrubin.core_language.ces_executor import CESExecutor
from scrubin.core_language.ces_validator import CESValidator
from scrubin.core_language.ces_bridge import CESBridge
from scrubin.core_language.ces_spec import CESScope
from scrubin.control_plane.replay.state import ReplayState
from scrubin.optimization.policy_compiler.policy_ir import CausalRuleIR

def run_phase_17_demo():
    print("=" * 60)
    print("  PHASE 17 — CAUSAL EXECUTION LANGUAGE (CES)")
    print("=" * 60)

    compiler = CESCompiler()
    executor = CESExecutor()
    validator = CESValidator()
    bridge = CESBridge()

    # ── 1. Compile RL Action → CES ──────────────────────────────
    print("\n[1/6] Compiling RL Action → CES Instruction...")
    rl_ces = compiler.compile_rl_action(
        action={"type": "ADMINISTER_OXYGEN", "flow_rate": 5},
        obs={"status": "UNSTABLE", "time": 10},
        reward=0.8,
        ceg_node="ceg_node_42"
    )
    print(f"  ID:     {rl_ces.id}")
    print(f"  Scope:  {rl_ces.scope.value}")
    print(f"  Action: {rl_ces.do.action}")
    print(f"  Anchor: {rl_ces.causal_anchor.ceg_node}")

    # ── 2. Compile Policy IR → CES ─────────────────────────────
    print("\n[2/6] Compiling Policy IR Rule → CES Instruction...")
    rule = CausalRuleIR(
        rule_id="RULE_0",
        condition="utilization > 0.85",
        intervention="ADJUST_TRIAGE",
        magnitude=0.15,
        causal_anchor="ceg_delta_node_7"
    )
    policy_ces = compiler.compile_policy_ir(rule)
    print(f"  ID:     {policy_ces.id}")
    print(f"  Scope:  {policy_ces.scope.value}")
    print(f"  When:   {policy_ces.when.trigger}")
    print(f"  Action: {policy_ces.do.action} ({policy_ces.do.params})")

    # ── 3. Compile Counterfactual → CES ────────────────────────
    print("\n[3/6] Compiling Counterfactual Delta → CES Instruction...")
    cf_ces = compiler.compile_counterfactual(
        delta={"mortality_delta": -1, "triage_shift": 0.12},
        variant_id="HIGH_TRIAGE_WORLD"
    )
    print(f"  ID:     {cf_ces.id}")
    print(f"  Scope:  {cf_ces.scope.value}")
    print(f"  Origin: {cf_ces.causal_anchor.counterfactual_origin}")

    # ── 4. Build & Validate CES Program ────────────────────────
    print("\n[4/6] Building Unified CES Program...")
    program = compiler.build_program([rl_ces, policy_ces, cf_ces], seed=42)
    print(f"  Program ID:    {program.program_id}")
    print(f"  Instructions:  {len(program.instructions)}")
    print(f"  Scopes:        {[i.scope.value for i in program.instructions]}")

    valid = validator.validate_program(program)
    print(f"  Structural Validation: {'PASS' if valid else 'FAIL'}")

    # ── 5. Execute CES Program Deterministically ───────────────
    print("\n[5/6] Executing CES Program against ReplayState...")
    state = ReplayState()
    final_state = executor.execute_program(program, state)

    accepted = [r for r in executor.execution_log if r.accepted]
    rejected = [r for r in executor.execution_log if not r.accepted]
    print(f"  Accepted: {len(accepted)}  Rejected: {len(rejected)}")
    print(f"  Final Tick: {final_state.tick}")
    print(f"  Decisions Recorded: {len(final_state.decisions)}")

    # ── 6. Determinism Verification ────────────────────────────
    print("\n[6/6] Verifying CES Determinism (dual execution)...")
    is_deterministic = validator.validate_determinism(program, CESExecutor(), ReplayState())
    print(f"  Bit-Identical Execution: {'MATCHED' if is_deterministic else 'DIVERGED'}")

    fp = validator.compute_program_fingerprint(program)
    print(f"  Program Fingerprint:     {fp[:16]}...")

    # ── Summary ────────────────────────────────────────────────
    if valid and is_deterministic:
        print("\n" + "=" * 60)
        print("  CES SYSTEM INVARIANTS VERIFIED")
        print("=" * 60)
        print("  ✔ RL → CES compilation (patient scope)")
        print("  ✔ Policy IR → CES compilation (hospital scope)")
        print("  ✔ Counterfactual → CES compilation (population scope)")
        print("  ✔ Structural validation (triggers, constraints)")
        print("  ✔ Deterministic execution (dual-run identity)")
        print("  ✔ Governance fingerprinting")
        print("=" * 60)

    print("\n--- Phase 17 CES Demo Complete ---")

if __name__ == "__main__":
    run_phase_17_demo()
