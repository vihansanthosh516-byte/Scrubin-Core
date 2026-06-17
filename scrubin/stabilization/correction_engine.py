"""Deterministic correction generation engine.

Maps `StabilityViolation`s to a deterministic `CorrectionPlan`.
All mappings are rule‑based; no heuristics or randomness.
"""

from __future__ import annotations

from .models import CorrectionAction, CorrectionPlan, StabilityViolation


class CorrectionEngine:
    @staticmethod
    def generate(violations: tuple[StabilityViolation, ...]) -> CorrectionPlan:
        actions: list[CorrectionAction] = []
        for v in violations:
            if v.description == "structural_oscillation":
                actions.append(CorrectionAction(target_component="system", action_type="normalize_structural", parameters=(v.severity,)))
            elif v.description == "behavioral_divergence":
                actions.append(CorrectionAction(target_component="behaviour", action_type="dampen_behavior", parameters=(v.severity,)))
            elif v.description == "physiological_instability":
                actions.append(CorrectionAction(target_component="physiology", action_type="adjust_thresholds", parameters=(v.severity,)))
            elif v.description == "cognitive_contradiction":
                actions.append(CorrectionAction(target_component="cognition", action_type="prune_beliefs", parameters=(v.severity,)))
        # Deterministic ordering by component then action_type.
        actions.sort(key=lambda a: (a.target_component, a.action_type, a.parameters))
        return CorrectionPlan(actions=tuple(actions))
