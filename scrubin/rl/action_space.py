from dataclasses import dataclass
from enum import IntEnum
from typing import List, Optional

from scrubin.models.intents import ActionIntent


class ClinicalAction(IntEnum):
    MONITOR = 0
    OXYGEN_THERAPY = 1
    INTUBATE = 2
    VASOPRESSORS = 3
    BLOOD_TRANSFUSION = 4
    IV_FLUIDS = 5
    ANTIBIOTICS = 6
    CENTRAL_LINE = 7
    BAG_MASK = 8
    VENTILATOR_ADJUSTMENT = 9
    EMERGENCY_AIRWAY = 10
    SURGICAL_INTERVENTION = 11
    WAIT = 12


_ACTION_NAMES: dict[ClinicalAction, str] = {
    ClinicalAction.MONITOR: "monitor",
    ClinicalAction.OXYGEN_THERAPY: "oxygen_therapy",
    ClinicalAction.INTUBATE: "intubation",
    ClinicalAction.VASOPRESSORS: "vasopressors",
    ClinicalAction.BLOOD_TRANSFUSION: "blood_transfusion",
    ClinicalAction.IV_FLUIDS: "iv_fluids",
    ClinicalAction.ANTIBIOTICS: "antibiotics",
    ClinicalAction.CENTRAL_LINE: "central_line",
    ClinicalAction.BAG_MASK: "bag_mask",
    ClinicalAction.VENTILATOR_ADJUSTMENT: "ventilator_adjustment",
    ClinicalAction.EMERGENCY_AIRWAY: "emergency_airway",
    ClinicalAction.SURGICAL_INTERVENTION: "surgical_intervention",
    ClinicalAction.WAIT: "wait",
}

_NAME_TO_ACTION: dict[str, ClinicalAction] = {v: k for k, v in _ACTION_NAMES.items()}


class ActionCategory(IntEnum):
    AIRWAY = 0
    CIRCULATION = 1
    INFECTION = 2
    GENERAL = 3


_CATEGORIES: dict[ClinicalAction, ActionCategory] = {
    ClinicalAction.MONITOR: ActionCategory.GENERAL,
    ClinicalAction.OXYGEN_THERAPY: ActionCategory.AIRWAY,
    ClinicalAction.INTUBATE: ActionCategory.AIRWAY,
    ClinicalAction.BAG_MASK: ActionCategory.AIRWAY,
    ClinicalAction.VENTILATOR_ADJUSTMENT: ActionCategory.AIRWAY,
    ClinicalAction.EMERGENCY_AIRWAY: ActionCategory.AIRWAY,
    ClinicalAction.VASOPRESSORS: ActionCategory.CIRCULATION,
    ClinicalAction.BLOOD_TRANSFUSION: ActionCategory.CIRCULATION,
    ClinicalAction.IV_FLUIDS: ActionCategory.CIRCULATION,
    ClinicalAction.CENTRAL_LINE: ActionCategory.CIRCULATION,
    ClinicalAction.ANTIBIOTICS: ActionCategory.INFECTION,
    ClinicalAction.SURGICAL_INTERVENTION: ActionCategory.GENERAL,
    ClinicalAction.WAIT: ActionCategory.GENERAL,
}


@dataclass(frozen=True)
class ActionMapping:
    action: ClinicalAction
    name: str
    category: ActionCategory


class RLActionSpace:
    def __init__(self, actions: Optional[List[ClinicalAction]] = None):
        self._actions = actions or list(ClinicalAction)
        self._mappings = {
            a: ActionMapping(
                action=a,
                name=_ACTION_NAMES[a],
                category=_CATEGORIES[a],
            )
            for a in self._actions
        }

    @property
    def n(self) -> int:
        return len(self._actions)

    @property
    def actions(self) -> List[ClinicalAction]:
        return list(self._actions)

    def mapping(self, action: ClinicalAction) -> ActionMapping:
        return self._mappings[action]

    def to_intent(
        self,
        action: ClinicalAction,
        target: str = "",
        confidence: float = 1.0,
        source: str = "rl_policy",
        reasoning: str = "",
    ) -> ActionIntent:
        m = self._mappings[action]
        return ActionIntent(
            id=f"rl-{action.value}-{target}",
            type="procedure",
            name=m.name,
            target=target,
            priority=float(action.value),
            confidence=confidence,
            source=source,
            reasoning=reasoning,
            metadata={"rl_action": action.value, "category": m.category.name},
        )

    def from_name(self, name: str) -> Optional[ClinicalAction]:
        return _NAME_TO_ACTION.get(name)

    def category(self, action: ClinicalAction) -> ActionCategory:
        return _CATEGORIES[action]

    def actions_in_category(self, category: ActionCategory) -> List[ClinicalAction]:
        return [a for a in self._actions if _CATEGORIES[a] == category]

    def to_dict(self) -> dict:
        return {
            "n": self.n,
            "actions": [
                {"value": a.value, "name": _ACTION_NAMES[a], "category": _CATEGORIES[a].name}
                for a in self._actions
            ],
        }
