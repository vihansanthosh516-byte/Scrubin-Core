from typing import Any, Dict
from scrubin.core_language.ces_spec import (
    CESInstruction, CESScope,
    CESCondition, CESAction, CESConstraints,
    CESCausalAnchor, CESObjective
)

class CESBridge:
    """
    Glue layer connecting all ScrubIn subsystems to the CES runtime.
    Translates live RL steps, multi-agent ticks, global decisions,
    and counterfactual experiments into CES instructions on-the-fly.
    """
    def from_rl_step(self, step_id: int, action: Dict, obs: Dict,
                     reward: float, ceg_node: str = "") -> CESInstruction:
        return CESInstruction(
            id=f"rl_step_{step_id}",
            scope=CESScope.PATIENT,
            when=CESCondition(trigger=f"tick={obs.get('time', 0)}"),
            do=CESAction(action=action.get("type", "OBSERVE"), params=action),
            constraints=CESConstraints(
                physiology="realism_score < 0.4",
                safety="phase14_gate"
            ),
            causal_anchor=CESCausalAnchor(ceg_node=ceg_node),
            objective=CESObjective(reward=reward)
        )

    def from_multiagent_action(self, agent_id: str, action: Dict,
                                priority: int, tick: int) -> CESInstruction:
        return CESInstruction(
            id=f"ma_{agent_id}_{tick}",
            scope=CESScope.HOSPITAL,
            when=CESCondition(trigger=f"tick={tick}", scope=CESScope.HOSPITAL),
            do=CESAction(action=action.get("type", "TREAT"), params=action),
            constraints=CESConstraints(
                resource=action.get("required_resource", ""),
                safety="phase14_gate"
            ),
            objective=CESObjective(reward=0.0)
        )

    def from_global_action(self, global_action: Any, tick: int) -> CESInstruction:
        return CESInstruction(
            id=f"global_{tick}",
            scope=CESScope.POPULATION,
            when=CESCondition(trigger=f"system_tick={tick}", scope=CESScope.POPULATION),
            do=CESAction(
                action="SYSTEM_INTERVENTION",
                params={
                    "triage": getattr(global_action, "triage_threshold", 0),
                    "response": getattr(global_action, "epidemic_response_level", 0)
                }
            ),
            constraints=CESConstraints(safety="phase14_gate")
        )
