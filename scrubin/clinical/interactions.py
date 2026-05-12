from dataclasses import dataclass
from typing import Optional


@dataclass
class InteractionEffect:
    target_complication: Optional[str] = None
    target_vital: Optional[str] = None
    severity_modifier: float = 0.0
    vital_delta: float = 0.0
    probability_multiplier: float = 1.0


@dataclass
class InteractionRule:
    source_complication: str
    effect: InteractionEffect


class InteractionEngine:
    def __init__(self):
        # Directed weighted interaction graph
        self.rules: list[InteractionRule] = [
            InteractionRule(
                source_complication="hemorrhage",
                effect=InteractionEffect(target_vital="bp_systolic", vital_delta=-5.0)
            ),
            InteractionRule(
                source_complication="hypoxia",
                effect=InteractionEffect(target_vital="heart_rate", vital_delta=3.0)
            ),
            InteractionRule(
                source_complication="thrombosis",
                effect=InteractionEffect(target_complication="hypoxia", probability_multiplier=1.5)
            ),
            InteractionRule(
                source_complication="infection",
                effect=InteractionEffect(target_vital="temperature", vital_delta=0.5)
            )
        ]

    def evaluate_vital_interactions(self, active_complications: list[str]) -> dict[str, float]:
        """Returns additive vital modifiers per tick based on active complications."""
        vital_modifiers = {}
        for comp in active_complications:
            for rule in self.rules:
                if rule.source_complication == comp and rule.effect.target_vital:
                    vital = rule.effect.target_vital
                    vital_modifiers[vital] = vital_modifiers.get(vital, 0.0) + rule.effect.vital_delta
        return vital_modifiers

    def evaluate_escalation_interactions(self, active_complications: list[str], target_comp: str) -> float:
        """Returns a multiplicative modifier for escalation probability."""
        multiplier = 1.0
        for comp in active_complications:
            for rule in self.rules:
                if rule.source_complication == comp and rule.effect.target_complication == target_comp:
                    multiplier *= rule.effect.probability_multiplier
        return multiplier
