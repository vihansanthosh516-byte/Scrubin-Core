"""Deterministic failure mode injection engine.

Maps adversarial conditions to concrete ``FailureMode`` objects that will be
applied to the simulation world later.
"""

from __future__ import annotations

from .models import AdversarialCondition, FailureMode


class FailureModeEngine:
    """Translate adversarial conditions into deterministic failure modes."""

    @staticmethod
    def map_conditions(conditions: tuple[AdversarialCondition, ...]) -> tuple[FailureMode, ...]:
        modes: list[FailureMode] = []
        for cond in conditions:
            if cond.description == "massive_bleeding":
                modes.append(FailureMode(component="cardiovascular", failure_type="hemorrhage_amplification"))
            elif cond.description == "hypoxia_risk":
                modes.append(FailureMode(component="respiratory", failure_type="airway_obstruction"))
            elif cond.description == "tool_malfunction":
                modes.append(FailureMode(component="instrument", failure_type="failure"))
        # Sort deterministically by component then failure_type
        modes.sort(key=lambda m: (m.component, m.failure_type))
        return tuple(modes)
