from typing import List, Optional

from scrubin.rl.action_space import ClinicalAction, RLActionSpace
from scrubin.safety.safety import SafetyShield
from scrubin.world.model import SimulationWorld


class EmergencyOverride:
    CRITICAL_MORTALITY_THRESHOLD = 0.8
    CRITICAL_SPO2_THRESHOLD = 60
    CRITICAL_MAP_THRESHOLD = 40

    def __init__(self, shield: SafetyShield, action_space: RLActionSpace | None = None):
        self._shield = shield
        self._action_space = action_space or RLActionSpace()
        self._overrides: List[dict] = []

    def check_emergency(self, world: SimulationWorld) -> Optional[ClinicalAction]:
        spo2 = world.physiology.vitals.get("spo2", 100)
        sys_bp = world.physiology.vitals.get("bp_systolic", 120)
        dia_bp = world.physiology.vitals.get("bp_diastolic", 80)
        map_val = (sys_bp + 2 * dia_bp) / 3.0
        if world.mortality_risk >= self.CRITICAL_MORTALITY_THRESHOLD:
            override = self._select_emergency_action(world)
            self._overrides.append({
                "tick": world.tick,
                "reason": f"mortality={world.mortality_risk:.2f}",
                "action": override.name if override else "none",
            })
            return override
        if spo2 < self.CRITICAL_SPO2_THRESHOLD:
            override_action = ClinicalAction.INTUBATE
            verdict = self._shield.evaluate(override_action, world)
            if verdict.allowed:
                self._overrides.append({"tick": world.tick, "reason": f"spo2={spo2}", "action": "intubate"})
                return override_action
            fallback = ClinicalAction.BAG_MASK
            self._overrides.append({"tick": world.tick, "reason": f"spo2={spo2}", "action": "bag_mask"})
            return fallback
        if map_val < self.CRITICAL_MAP_THRESHOLD:
            override_action = ClinicalAction.VASOPRESSORS
            verdict = self._shield.evaluate(override_action, world)
            if verdict.allowed:
                self._overrides.append({"tick": world.tick, "reason": f"map={map_val:.1f}", "action": "vasopressors"})
                return override_action
            fallback = ClinicalAction.IV_FLUIDS
            self._overrides.append({"tick": world.tick, "reason": f"map={map_val:.1f}", "action": "iv_fluids"})
            return fallback
        return None

    def _select_emergency_action(self, world: SimulationWorld) -> Optional[ClinicalAction]:
        emergency_actions = [
            ClinicalAction.INTUBATE,
            ClinicalAction.VASOPRESSORS,
            ClinicalAction.BLOOD_TRANSFUSION,
            ClinicalAction.EMERGENCY_AIRWAY,
            ClinicalAction.IV_FLUIDS,
        ]
        for action in emergency_actions:
            verdict = self._shield.evaluate(action, world)
            if verdict.allowed:
                return action
        return ClinicalAction.MONITOR

    @property
    def overrides(self) -> List[dict]:
        return list(self._overrides)

    @property
    def num_overrides(self) -> int:
        return len(self._overrides)

    def clear(self) -> None:
        self._overrides.clear()
