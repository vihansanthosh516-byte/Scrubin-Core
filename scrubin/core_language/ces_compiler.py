from typing import Any, Dict
from scrubin.core_language.ces_spec import (
    CESInstruction, CESProgram, CESScope,
    CESCondition, CESAction, CESConstraints,
    CESCausalAnchor, CESObjective
)

class CESCompiler:
    """
    Universal compiler: Translates RL actions, Policy IR, Global Policies,
    and Counterfactual rules into CES programs.
    """
    def compile_rl_action(self, action: Dict[str, Any], obs: Dict[str, Any],
                          reward: float, ceg_node: str = "") -> CESInstruction:
        return CESInstruction(
            id=f"rl_{action.get('type', 'unknown')}",
            scope=CESScope.PATIENT,
            when=CESCondition(trigger=f"obs_state={obs.get('status', 'STABLE')}"),
            do=CESAction(action=action.get("type", "OBSERVE"), params=action),
            constraints=CESConstraints(physiology="realism_score < 0.4", safety="phase14_gate"),
            causal_anchor=CESCausalAnchor(ceg_node=ceg_node),
            objective=CESObjective(reward=reward, penalty_model="Phase15.1")
        )

    def compile_policy_ir(self, rule: Any) -> CESInstruction:
        return CESInstruction(
            id=f"policy_{rule.rule_id}",
            scope=CESScope.HOSPITAL,
            when=CESCondition(trigger=rule.condition, scope=CESScope.HOSPITAL),
            do=CESAction(action=rule.intervention, params={"magnitude": rule.magnitude}),
            constraints=CESConstraints(safety="phase14_gate"),
            causal_anchor=CESCausalAnchor(ceg_node=rule.causal_anchor),
            objective=CESObjective(reward=0.0)
        )

    def compile_global_policy(self, global_action: Any) -> CESInstruction:
        return CESInstruction(
            id="global_meta_action",
            scope=CESScope.POPULATION,
            when=CESCondition(trigger="system_tick", scope=CESScope.POPULATION),
            do=CESAction(
                action="SYSTEM_INTERVENTION",
                params={
                    "triage_threshold": global_action.triage_threshold,
                    "epidemic_response": global_action.epidemic_response_level
                }
            ),
            constraints=CESConstraints(safety="phase14_gate", resource="global_budget"),
            objective=CESObjective(reward=0.0)
        )

    def compile_counterfactual(self, delta: Dict[str, Any], variant_id: str) -> CESInstruction:
        return CESInstruction(
            id=f"cf_{variant_id}",
            scope=CESScope.POPULATION,
            when=CESCondition(trigger="counterfactual_branch"),
            do=CESAction(action="POLICY_VARIANT", params=delta),
            constraints=CESConstraints(safety="phase14_gate", physiology="counterfactual_bounded"),
            causal_anchor=CESCausalAnchor(counterfactual_origin=variant_id),
            objective=CESObjective(reward=delta.get("mortality_delta", 0) * -1.0)
        )

    def build_program(self, instructions: list, seed: int = 0) -> CESProgram:
        prog = CESProgram(program_id=f"ces_prog_{seed}", seed=seed)
        for inst in instructions:
            prog.add(inst)
        return prog
