from dataclasses import dataclass
from typing import Callable, List, Optional

from scrubin.rl.action_space import ClinicalAction
from scrubin.world.model import SimulationWorld


SafetyRule = Callable[[ClinicalAction, SimulationWorld], bool]


def _no_extubate_severe_hypoxia(action: ClinicalAction, world: SimulationWorld) -> bool:
    if action == ClinicalAction.WAIT:
        spo2 = world.physiology.vitals.get("spo2", 100)
        if spo2 < 70:
            return False
    return True


def _no_ventilator_over_capacity(action: ClinicalAction, world: SimulationWorld) -> bool:
    if action in (ClinicalAction.INTUBATE, ClinicalAction.VENTILATOR_ADJUSTMENT, ClinicalAction.EMERGENCY_AIRWAY):
        vents = world.resource_manager.resources.get("ventilators")
        if vents and vents.available <= 0:
            return False
    return True


def _no_negative_blood(action: ClinicalAction, world: SimulationWorld) -> bool:
    if action == ClinicalAction.BLOOD_TRANSFUSION:
        blood = world.resource_manager.resources.get("blood_units")
        if blood and blood.available <= 0:
            return False
    return True


def _no_ignore_terminal_shock(action: ClinicalAction, world: SimulationWorld) -> bool:
    if action in (ClinicalAction.MONITOR, ClinicalAction.WAIT):
        sys_bp = world.physiology.vitals.get("bp_systolic", 120)
        dia_bp = world.physiology.vitals.get("bp_diastolic", 80)
        map_val = (sys_bp + 2 * dia_bp) / 3.0
        if map_val < 50 and world.mortality_risk > 0.5:
            return False
    return True


def _no_overtreat_stable(action: ClinicalAction, world: SimulationWorld) -> bool:
    if action in (ClinicalAction.INTUBATE, ClinicalAction.EMERGENCY_AIRWAY, ClinicalAction.VASOPRESSORS):
        if world.mortality_risk < 0.02 and world.news2_score < 3:
            return False
    return True


CANONICAL_SAFETY_RULES: List[SafetyRule] = [
    _no_extubate_severe_hypoxia,
    _no_ventilator_over_capacity,
    _no_negative_blood,
    _no_ignore_terminal_shock,
    _no_overtreat_stable,
]


@dataclass
class SafetyConstraint:
    rule_id: str
    description: str
    rule: SafetyRule

    def check(self, action: ClinicalAction, world: SimulationWorld) -> bool:
        return self.rule(action, world)


CANONICAL_CONSTRAINTS: List[SafetyConstraint] = [
    SafetyConstraint(rule_id="safety.no_wait_under_hypoxia", description="Cannot wait under severe hypoxia (SpO2 < 70)", rule=_no_extubate_severe_hypoxia),
    SafetyConstraint(rule_id="safety.no_ventilator_over_capacity", description="Cannot intubate when ventilators are at capacity", rule=_no_ventilator_over_capacity),
    SafetyConstraint(rule_id="safety.no_negative_blood", description="Cannot transfuse when no blood units available", rule=_no_negative_blood),
    SafetyConstraint(rule_id="safety.no_ignore_terminal_shock", description="Cannot monitor/wait under terminal shock (MAP < 50, mortality > 0.5)", rule=_no_ignore_terminal_shock),
    SafetyConstraint(rule_id="safety.no_overtreat_stable", description="Cannot intubate/vasopressors for stable patients", rule=_no_overtreat_stable),
]
