"""Deterministic adversarial condition engine.

Creates deterministic ``AdversarialCondition`` objects based on the scenario
seed and previously generated stress vectors.  The rule set is simple:
* If hemorrhage stress present → add "massive_bleeding" condition.
* If airway stress present → add "hypoxia_risk" condition.
* If instrument failure present → add "tool_malfunction" condition.
All conditions are sorted deterministically by description.
"""

from __future__ import annotations

from .models import ScenarioSeed, StressVector, AdversarialCondition


class AdversarialScenarioEngine:
    """Generate deterministic adversarial conditions from a seed and stress vectors."""

    @staticmethod
    def generate(seed: ScenarioSeed, stresses: tuple[StressVector, ...]) -> tuple[AdversarialCondition, ...]:
        conditions: list[AdversarialCondition] = []
        names = {sv.name for sv in stresses}
        if "hemorrhage_amplification" in names:
            conditions.append(AdversarialCondition(description="massive_bleeding", severity=0.8))
        if "airway_obstruction" in names:
            conditions.append(AdversarialCondition(description="hypoxia_risk", severity=0.6))
        if "instrument_failure" in names:
            conditions.append(AdversarialCondition(description="tool_malfunction", severity=0.5))
        # Deterministic ordering by description
        conditions.sort(key=lambda c: c.description)
        return tuple(conditions)
