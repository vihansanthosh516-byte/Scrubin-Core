from __future__ import annotations

"""Deterministic tutoring and coaching engine.

Generates deterministic coaching interventions based on repeated unsafe maneuvers,
semantic fixation, overload collapse, workflow inefficiency, strategic adaptation
issues, contamination neglect, and anatomy misunderstanding.
"""

from dataclasses import dataclass, field, replace
from typing import List, Tuple


from scrubin.execution.state import TechnicalExecutionState
from scrubin.ontology.attention_state import AttentionState
from scrubin.ontology.overload_state import OverloadState


@dataclass(frozen=True)
class CoachingIntervention:
    intervention_id: str
    intervention_type: str  # e.g., "remediation", "strategy", "safety"
    target_domain: str
    severity: float = 0.0  # 0‑1
    explanation: str = ""
    recommended_action: str = ""
    semantic_tags: Tuple[str, ...] = field(default_factory=tuple)
    priority: float = 0.0  # higher = more urgent

    def with_severity(self, v: float) -> "CoachingIntervention":
        return replace(self, severity=max(0.0, min(1.0, v)))

    def with_priority(self, v: float) -> "CoachingIntervention":
        return replace(self, priority=v)

    def with_explanation(self, txt: str) -> "CoachingIntervention":
        return replace(self, explanation=txt)

    def with_recommended_action(self, txt: str) -> "CoachingIntervention":
        return replace(self, recommended_action=txt)

    def add_semantic_tag(self, tag: str) -> "CoachingIntervention":
        return replace(self, semantic_tags=self.semantic_tags + (tag,))


@dataclass(frozen=True)
class TutoringState:
    active_interventions: Tuple[CoachingIntervention, ...] = field(default_factory=tuple)
    intervention_history: Tuple[str, ...] = field(default_factory=tuple)
    coaching_load: float = 0.0  # 0‑1 aggregate load
    tutoring_mode: str = ""
    adaptive_guidance_level: float = 0.0  # 0‑1
    remediation_focus: Tuple[str, ...] = field(default_factory=tuple)
    tutoring_tick: int = 0

    # deterministic helpers
    def add_intervention(self, interv: CoachingIntervention) -> "TutoringState":
        new_active = self.active_interventions + (interv,)
        new_history = self.intervention_history + (interv.intervention_id,)
        new_load = min(1.0, self.coaching_load + interv.severity)
        return replace(self, active_interventions=new_active, intervention_history=new_history, coaching_load=new_load)

    def with_tutoring_mode(self, mode: str) -> "TutoringState":
        return replace(self, tutoring_mode=mode)

    def with_adaptive_guidance_level(self, level: float) -> "TutoringState":
        return replace(self, adaptive_guidance_level=max(0.0, min(1.0, level)))

    def with_remediation_focus(self, focus: Tuple[str, ...]) -> "TutoringState":
        return replace(self, remediation_focus=focus)

    def with_tutoring_tick(self, tick: int) -> "TutoringState":
        return replace(self, tutoring_tick=tick)

    def clear_completed_interventions(self) -> "TutoringState":
        # For deterministic simplicity, we clear all active interventions each tick.
        return replace(self, active_interventions=tuple())


class TutoringEngine:
    """Deterministically generate coaching interventions based on observed deficiencies."""

    def __init__(self, rng) -> None:
        self.rng = rng  # retained for future tie‑breaks

    def coach(self, world: "WorldState") -> "WorldState":
        tech: TechnicalExecutionState = getattr(world, "technical_execution_state", TechnicalExecutionState())
        overload: OverloadState = getattr(world, "overload_state", OverloadState())
        attention: AttentionState = getattr(world, "attention_state", AttentionState())
        tutoring: TutoringState = getattr(world, "tutoring_state", TutoringState())
        from scrubin.core.events import TimelineEvent
        events: List[TimelineEvent] = []

        # Determine deterministic triggers
        interventions: List[CoachingIntervention] = []
        # Repeated unsafe maneuvers
        if len(tech.failed_maneuvers) > 0:
            for idx, man in enumerate(tech.failed_maneuvers[-3:]):  # last three failures
                interv = CoachingIntervention(
                    intervention_id=f"unsafe_{man}_{world.tick}_{idx}",
                    intervention_type="safety",
                    target_domain="technical_precision",
                    severity=0.3,
                    explanation=f"Maneuver '{man}' failed – improve precision.",
                    recommended_action="Reduce force, increase visualization quality.",
                    semantic_tags=("precision", "force"),
                    priority=0.7,
                )
                interventions.append(interv)
                events.append(TimelineEvent(world.tick, "coaching_intervention_generated"))

        # Semantic fixation – simple proxy via attention load vs capacity
        if attention.current_load > attention.overload_threshold:
            interv = CoachingIntervention(
                intervention_id=f"semantic_fix_{world.tick}",
                intervention_type="semantic",
                target_domain="semantic_understanding",
                severity=0.2,
                explanation="High attention load indicates possible fixation.",
                recommended_action="Review semantic context, pause and reassess.",
                semantic_tags=("attention", "load"),
                priority=0.6,
            )
            interventions.append(interv)
            events.append(TimelineEvent(world.tick, "semantic_remediation_triggered"))

        # Overload collapse – proxy via overload level
        if overload.overload_level > 0.6:
            interv = CoachingIntervention(
                intervention_id=f"overload_coach_{world.tick}",
                intervention_type="overload",
                target_domain="overload_resilience",
                severity=0.25,
                explanation="Operator overload high – risk of collapse.",
                recommended_action="Decrease task‑switch penalty, allow recovery.",
                semantic_tags=("overload",),
                priority=0.8,
            )
            interventions.append(interv)
            events.append(TimelineEvent(world.tick, "overload_coaching_activated"))

        # Workflow inefficiency – proxy via execution latency
        if tech.execution_latency > 2:
            interv = CoachingIntervention(
                intervention_id=f"workflow_eff_{world.tick}",
                intervention_type="workflow",
                target_domain="workflow_friction",
                severity=0.15,
                explanation="Execution latency elevated – possible workflow bottleneck.",
                recommended_action="Review handoffs, streamline transitions.",
                semantic_tags=("latency",),
                priority=0.5,
            )
            interventions.append(interv)
            events.append(TimelineEvent(world.tick, "workflow_efficiency_guidance_generated"))

        # Apply deterministic ordering to interventions (by id)
        interventions_sorted = sorted(interventions, key=lambda i: i.intervention_id)
        # Update tutoring state deterministically
        new_tutoring = tutoring.clear_completed_interventions()
        for interv in interventions_sorted:
            new_tutoring = new_tutoring.add_intervention(interv)

        new_tutoring = new_tutoring.with_tutoring_tick(world.tick)
        new_world = world.with_tutoring_state(new_tutoring)
        for ev in events:
            new_world = new_world.append_timeline(ev)
        return new_world
