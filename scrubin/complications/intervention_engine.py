"""Deterministic Intervention Recommendation Engine.
+
+The engine examines the current immutable ``ComplicationState`` together with
+snapshots of physiology, anatomy, OR team, and workflow.  It produces a
+``RecommendationSet`` containing an ordered tuple of ``InterventionRecommendation``
+objects.  All logic is pure and deterministic – decisions are derived from a set
+of explicit rule tables rather than any probabilistic model.
+"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Tuple, Mapping, Any, List

from .models import Complication, ComplicationState


@dataclass(frozen=True, slots=True)
class InterventionRecommendation:
    """Single immutable recommendation.
+
+    ``action`` is a short identifier such as ``"apply_pressure"``.  ``detail``
+    may carry additional deterministic context.
+    """

    complication_id: int
    action: str
    detail: Any = None

    def __lt__(self, other: "InterventionRecommendation") -> bool:
        # Deterministic ordering first by complication_id then by action
        if self.complication_id != other.complication_id:
            return self.complication_id < other.complication_id
        return self.action < other.action


@dataclass(frozen=True, slots=True)
class RecommendationSet:
    """Immutable collection of ordered recommendations.
+
+    ``recommendations`` are stored as a sorted tuple to guarantee deterministic
+    reproducibility across runs.
+    """

    recommendations: Tuple[InterventionRecommendation, ...] = ()

    def with_added(self, rec: InterventionRecommendation) -> "RecommendationSet":
        new_recs = list(self.recommendations) + [rec]
        new_recs.sort()
        return replace(self, recommendations=tuple(new_recs))


class InterventionEngine:
    """Pure engine that emits deterministic intervention recommendations.
+
+    The rule set is intentionally simple and fully deterministic:
+    * For each active complication, inspect its ``complication_type`` and
+      ``severity``.
+    * Based on predefined mappings (see ``_RULES``) emit one or more
+      ``InterventionRecommendation`` objects.
+    * Additional context from ``physiology``, ``anatomy``, ``or_team`` and
+      ``workflow`` can enable extra recommendations (e.g., low ``blood_pressure``
+      triggers ``administer_fluids``).
+    The method returns a ``RecommendationSet``; the caller can further combine
+    sets if needed.
+    """

    # Simple deterministic rule table – maps (type, severity) to list of actions
    _RULES: Mapping[tuple[str, int], List[str]] = {
        ("bleed", 1): ["apply_pressure", "suction_field"],
        ("bleed", 2): ["clip_vessel", "cauterize"],
        ("bleed", 3): ["clip_vessel", "cauterize", "call_vascular_surgeon"],
        ("infection", 1): ["administer_fluids", "increase_FiO2"],
        ("infection", 2): ["administer_fluids", "administer_vasopressor", "increase_FiO2"],
        ("infection", 3): ["administer_fluids", "administer_vasopressor", "call_vascular_surgeon"],
        ("cardiac", 1): ["pause_procedure", "obtain_exposure"],
        ("cardiac", 2): ["pause_procedure", "call_vascular_surgeon"],
    }

    @staticmethod
    def evaluate(
        state: ComplicationState,
        physiology: Mapping[str, Any],
        anatomy: Mapping[str, Any],
        or_team: Mapping[str, Any],
        workflow: Mapping[str, Any],
    ) -> RecommendationSet:
        rec_set = RecommendationSet()
        for comp in state.active_complications:
            key = (comp.complication_type, comp.severity)
            actions = InterventionEngine._RULES.get(key, [])
            for act in actions:
                rec = InterventionRecommendation(complication_id=comp.deterministic_id, action=act)
                rec_set = rec_set.with_added(rec)

        # Additional deterministic checks based on global state
        if physiology.get("blood_pressure", 120) < 80:
            # low BP -> fluids for all active complications
            for comp in state.active_complications:
                rec_set = rec_set.with_added(
                    InterventionRecommendation(complication_id=comp.deterministic_id, action="administer_fluids")
                )
        if or_team.get("staff_available", 1) < 1:
            # understaffed -> convert to open for all
            for comp in state.active_complications:
                rec_set = rec_set.with_added(
                    InterventionRecommendation(complication_id=comp.deterministic_id, action="convert_to_open")
                )
        if workflow.get("emergency", False):
            for comp in state.active_complications:
                rec_set = rec_set.with_added(
                    InterventionRecommendation(complication_id=comp.deterministic_id, action="pause_procedure")
                )
        return rec_set
