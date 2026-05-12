from dataclasses import dataclass
from typing import List, Optional

from scrubin.rl.action_space import ClinicalAction, RLActionSpace
from scrubin.world.model import SimulationWorld
from scrubin.safety.constraints import SafetyConstraint, CANONICAL_CONSTRAINTS


@dataclass
class ShieldVerdict:
    action: ClinicalAction
    allowed: bool
    violations: List[str]
    fallback_action: Optional[ClinicalAction] = None

    def to_dict(self) -> dict:
        return {
            "action": self.action.name,
            "allowed": self.allowed,
            "violations": self.violations,
            "fallback_action": self.fallback_action.name if self.fallback_action else None,
        }


class SafetyShield:
    def __init__(
        self,
        constraints: List[SafetyConstraint] | None = None,
        action_space: RLActionSpace | None = None,
        default_fallback: ClinicalAction = ClinicalAction.MONITOR,
    ):
        self._constraints = constraints or list(CANONICAL_CONSTRAINTS)
        self._action_space = action_space or RLActionSpace()
        self._default_fallback = default_fallback
        self._block_log: List[ShieldVerdict] = []

    def evaluate(self, action: ClinicalAction, world: SimulationWorld) -> ShieldVerdict:
        violations = []
        for constraint in self._constraints:
            if not constraint.check(action, world):
                violations.append(constraint.rule_id)
        allowed = len(violations) == 0
        fallback = None
        if not allowed:
            fallback = self._find_safe_fallback(action, world)
        verdict = ShieldVerdict(
            action=action,
            allowed=allowed,
            violations=violations,
            fallback_action=fallback,
        )
        if not allowed:
            self._block_log.append(verdict)
        return verdict

    def shield_action(self, action: ClinicalAction, world: SimulationWorld) -> ClinicalAction:
        verdict = self.evaluate(action, world)
        if verdict.allowed:
            return action
        if verdict.fallback_action is not None:
            return verdict.fallback_action
        return self._default_fallback

    def _find_safe_fallback(self, blocked_action: ClinicalAction, world: SimulationWorld) -> Optional[ClinicalAction]:
        safe_actions = []
        for action in self._action_space.actions:
            if action == blocked_action:
                continue
            if self._check_constraints_direct(action, world):
                safe_actions.append(action)
        if safe_actions:
            priority_order = [
                ClinicalAction.VASOPRESSORS,
                ClinicalAction.INTUBATE,
                ClinicalAction.OXYGEN_THERAPY,
                ClinicalAction.IV_FLUIDS,
                ClinicalAction.BLOOD_TRANSFUSION,
                ClinicalAction.ANTIBIOTICS,
                ClinicalAction.BAG_MASK,
                ClinicalAction.CENTRAL_LINE,
                ClinicalAction.VENTILATOR_ADJUSTMENT,
                ClinicalAction.EMERGENCY_AIRWAY,
                ClinicalAction.SURGICAL_INTERVENTION,
                ClinicalAction.MONITOR,
                ClinicalAction.WAIT,
            ]
            for candidate in priority_order:
                if candidate in safe_actions:
                    return candidate
        return None

    def _check_constraints_direct(self, action: ClinicalAction, world: SimulationWorld) -> bool:
        for constraint in self._constraints:
            if not constraint.check(action, world):
                return False
        return True

    @property
    def block_log(self) -> List[ShieldVerdict]:
        return list(self._block_log)

    @property
    def num_blocks(self) -> int:
        return len(self._block_log)

    def clear_log(self) -> None:
        self._block_log.clear()
