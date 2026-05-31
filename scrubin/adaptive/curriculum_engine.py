from __future__ import annotations

"""Deterministic adaptive curriculum engine.

Generates and evolves curriculum objectives based on operator competency, recent performance,
and system state. All updates are immutable.
"""

from dataclasses import dataclass, field, replace
from typing import List, Tuple


from scrubin.adaptive.competency import OperatorCompetencyProfile


@dataclass(frozen=True)
class CurriculumObjective:
    objective_id: str
    target_domain: str
    target_skill: str
    mastery_threshold: float = 0.8  # 0‑1
    remediation_required: bool = False
    semantic_focus: Tuple[str, ...] = field(default_factory=tuple)
    procedural_focus: Tuple[str, ...] = field(default_factory=tuple)
    completion_state: float = 0.0  # 0‑1 progress

    # deterministic helpers
    def with_completion_state(self, v: float) -> "CurriculumObjective":
        return replace(self, completion_state=max(0.0, min(1.0, v)))

    def with_remediation_required(self, v: bool) -> "CurriculumObjective":
        return replace(self, remediation_required=v)


@dataclass(frozen=True)
class AdaptiveCurriculum:
    active_objectives: Tuple[CurriculumObjective, ...] = field(default_factory=tuple)
    completed_objectives: Tuple[CurriculumObjective, ...] = field(default_factory=tuple)
    curriculum_phase: str = ""
    curriculum_complexity: float = 0.0
    remediation_queue: Tuple[CurriculumObjective, ...] = field(default_factory=tuple)
    advancement_readiness: float = 0.0
    curriculum_tick: int = 0

    # deterministic helpers
    def with_active_objectives(self, objs: Tuple[CurriculumObjective, ...]) -> "AdaptiveCurriculum":
        return replace(self, active_objectives=tuple(sorted(objs, key=lambda o: o.objective_id)))

    def with_completed_objectives(self, objs: Tuple[CurriculumObjective, ...]) -> "AdaptiveCurriculum":
        return replace(self, completed_objectives=tuple(sorted(objs, key=lambda o: o.objective_id)))

    def with_curriculum_phase(self, phase: str) -> "AdaptiveCurriculum":
        return replace(self, curriculum_phase=phase)

    def with_curriculum_complexity(self, v: float) -> "AdaptiveCurriculum":
        return replace(self, curriculum_complexity=v)

    def with_remediation_queue(self, queue: Tuple[CurriculumObjective, ...]) -> "AdaptiveCurriculum":
        return replace(self, remediation_queue=tuple(sorted(queue, key=lambda o: o.objective_id)))

    def with_advancement_readiness(self, v: float) -> "AdaptiveCurriculum":
        return replace(self, advancement_readiness=v)

    def with_curriculum_tick(self, tick: int) -> "AdaptiveCurriculum":
        return replace(self, curriculum_tick=tick)

    def add_active_objective(self, obj: CurriculumObjective) -> "AdaptiveCurriculum":
        new_active = self.active_objectives + (obj,)
        return replace(self, active_objectives=tuple(sorted(new_active, key=lambda o: o.objective_id)))

    def mark_objective_completed(self, objective_id: str) -> "AdaptiveCurriculum":
        completed = tuple(o for o in self.active_objectives if o.objective_id == objective_id)
        remaining = tuple(o for o in self.active_objectives if o.objective_id != objective_id)
        new_completed = self.completed_objectives + completed
        return replace(self, active_objectives=remaining, completed_objectives=tuple(sorted(new_completed, key=lambda o: o.objective_id)))

    def add_to_remediation_queue(self, obj: CurriculumObjective) -> "AdaptiveCurriculum":
        new_queue = self.remediation_queue + (obj,)
        return replace(self, remediation_queue=tuple(sorted(new_queue, key=lambda o: o.objective_id)))


from scrubin.core.events import TimelineEvent

class CurriculumEngine:
    """Deterministically evolve the adaptive curriculum based on competency and performance."""

    def __init__(self, rng) -> None:
        self.rng = rng  # retained for future tie‑breaks

    def evolve(self, world: "WorldState") -> "WorldState":
        comp: OperatorCompetencyProfile = getattr(world, "operator_competency_profile", OperatorCompetencyProfile())
        curriculum: AdaptiveCurriculum = getattr(world, "adaptive_curriculum", AdaptiveCurriculum())
        events: List[TimelineEvent] = []

        # Determine readiness – simple deterministic function of overall competency and recent growth
        readiness = (comp.overall_competency + comp.longitudinal_growth) / 2.0
        curriculum = curriculum.with_advancement_readiness(readiness)

        # If readiness exceeds a threshold, add a new advanced objective
        if readiness > 0.7 and len(curriculum.active_objectives) < 3:
            new_obj = CurriculumObjective(
                objective_id=f"obj_{world.tick}",
                target_domain="general",
                target_skill="technical_precision",
                mastery_threshold=0.85,
                remediation_required=False,
                semantic_focus=("precision", "force"),
                procedural_focus=("maneuver_execution",),
                completion_state=0.0,
            )
            curriculum = curriculum.add_active_objective(new_obj)
            events.append(TimelineEvent(world.tick, "curriculum_objective_added"))

        # Check for any active objective that has reached mastery (deterministic proxy via competency domain values)
        completed_ids = []
        for obj in curriculum.active_objectives:
            # Simple deterministic check: if overall competency exceeds the objective's mastery threshold
            if comp.overall_competency >= obj.mastery_threshold:
                completed_ids.append(obj.objective_id)
                events.append(TimelineEvent(world.tick, "curriculum_advancement_ready"))
                # If remediation required, move to remediation queue
                if obj.remediation_required:
                    curriculum = curriculum.add_to_remediation_queue(obj)
                    events.append(TimelineEvent(world.tick, "remediation_pathway_created"))
        for oid in completed_ids:
            curriculum = curriculum.mark_objective_completed(oid)

        # If enough objectives completed, unlock a higher curriculum phase
        if len(curriculum.completed_objectives) >= 5 and curriculum.curriculum_phase != "advanced":
            curriculum = curriculum.with_curriculum_phase("advanced")
            events.append(TimelineEvent(world.tick, "advanced_semantic_module_unlocked"))

        # If readiness insufficient, possibly emit a competency gate failure
        if readiness < 0.3:
            events.append(TimelineEvent(world.tick, "competency_gate_failed"))

        # Update tick
        curriculum = curriculum.with_curriculum_tick(world.tick)

        new_world = world.with_adaptive_curriculum(curriculum)
        for ev in events:
            new_world = new_world.append_timeline(ev)
        return new_world
