"""Deterministic stability assessment engine.

Evaluates a `DriftVector` and produces a `SystemStabilityState` with ordered
violations.  The logic is rule‑based and fully deterministic.
"""

from __future__ import annotations

from .models import SystemStabilityState, StabilityViolation


class StabilityEngine:
    @staticmethod
    def assess(drift) -> SystemStabilityState:
        violations: list[StabilityViolation] = []
        score = 1.0
        # Simple deterministic thresholds.
        if drift.structural_drift > 0.2:
            violations.append(StabilityViolation(description="structural_oscillation", severity=drift.structural_drift))
            score -= 0.2
        if drift.behavioral_drift > 0.2:
            violations.append(StabilityViolation(description="behavioral_divergence", severity=drift.behavioral_drift))
            score -= 0.2
        if drift.physiological_drift > 0.2:
            violations.append(StabilityViolation(description="physiological_instability", severity=drift.physiological_drift))
            score -= 0.2
        if drift.cognitive_drift > 0.2:
            violations.append(StabilityViolation(description="cognitive_contradiction", severity=drift.cognitive_drift))
            score -= 0.2
        # Sort violations deterministically.
        violations.sort(key=lambda v: (v.description, v.severity))
        return SystemStabilityState(stability_score=max(0.0, score), violations=tuple(violations))
