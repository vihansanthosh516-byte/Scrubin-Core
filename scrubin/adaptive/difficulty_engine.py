from __future__ import annotations

"""Adaptive difficulty engine – deterministic scaling of simulation difficulty based on competency and recent performance."""

from dataclasses import dataclass, replace
from typing import List


from scrubin.adaptive.competency import OperatorCompetencyProfile
from scrubin.execution.state import TechnicalExecutionState
from scrubin.ontology.overload_state import OverloadState
from scrubin.ontology.attention_state import AttentionState


@dataclass(frozen=True)
class DifficultyProfile:
    global_difficulty: float = 0.0  # 0‑1, higher = more difficult
    physiologic_instability_multiplier: float = 1.0
    complication_frequency_multiplier: float = 1.0
    workflow_friction_multiplier: float = 1.0
    semantic_complexity_multiplier: float = 1.0
    cognitive_load_multiplier: float = 1.0
    contamination_risk_multiplier: float = 1.0
    strategic_instability_multiplier: float = 1.0
    recovery_penalty_multiplier: float = 1.0
    assistance_level: float = 0.0  # 0‑1, higher = more assistance
    adaptation_tick: int = 0

    # deterministic with_* helpers
    def with_global_difficulty(self, v: float) -> "DifficultyProfile":
        return replace(self, global_difficulty=max(0.0, min(1.0, v)))

    def with_physiologic_instability_multiplier(self, v: float) -> "DifficultyProfile":
        return replace(self, physiologic_instability_multiplier=v)

    def with_complication_frequency_multiplier(self, v: float) -> "DifficultyProfile":
        return replace(self, complication_frequency_multiplier=v)

    def with_workflow_friction_multiplier(self, v: float) -> "DifficultyProfile":
        return replace(self, workflow_friction_multiplier=v)

    def with_semantic_complexity_multiplier(self, v: float) -> "DifficultyProfile":
        return replace(self, semantic_complexity_multiplier=v)

    def with_cognitive_load_multiplier(self, v: float) -> "DifficultyProfile":
        return replace(self, cognitive_load_multiplier=v)

    def with_contamination_risk_multiplier(self, v: float) -> "DifficultyProfile":
        return replace(self, contamination_risk_multiplier=v)

    def with_strategic_instability_multiplier(self, v: float) -> "DifficultyProfile":
        return replace(self, strategic_instability_multiplier=v)

    def with_recovery_penalty_multiplier(self, v: float) -> "DifficultyProfile":
        return replace(self, recovery_penalty_multiplier=v)

    def with_assistance_level(self, v: float) -> "DifficultyProfile":
        return replace(self, assistance_level=max(0.0, min(1.0, v)))

    def with_adaptation_tick(self, tick: int) -> "DifficultyProfile":
        return replace(self, adaptation_tick=tick)


class AdaptiveDifficultyEngine:
    """Deterministically adapt difficulty based on competency and recent performance."""

    def __init__(self, rng) -> None:
        self.rng = rng  # retained for future tie‑breaks

    def adapt(self, world: "WorldState") -> "WorldState":
        comp: OperatorCompetencyProfile = getattr(world, "operator_competency_profile", OperatorCompetencyProfile())
        diff: DifficultyProfile = getattr(world, "difficulty_profile", DifficultyProfile())
        tech: TechnicalExecutionState = getattr(world, "technical_execution_state", TechnicalExecutionState())
        overload: OverloadState = getattr(world, "overload_state", OverloadState())
        attention: AttentionState = getattr(world, "attention_state", AttentionState())
        from scrubin.core.events import TimelineEvent
        events: List[TimelineEvent] = []

        # Determine target difficulty based on overall competency and recent overload periods.
        # Higher competency => higher difficulty, but cap to avoid runaway.
        target = comp.overall_competency * 0.8 + comp.adaptability_score * 0.1
        # Reduce difficulty if recent overload is high.
        if overload.overload_level > 0.5:
            target *= 0.7
        # Adjust for recent failures (simple deterministic proxy via failed maneuvers count)
        failure_factor = len(tech.failed_maneuvers) * 0.02
        target = max(0.0, min(1.0, target - failure_factor))

        # Apply a bounded step change to avoid abrupt jumps (deterministic step of 0.01)
        current = diff.global_difficulty
        if abs(target - current) < 0.01:
            new_global = target
        elif target > current:
            new_global = current + 0.01
        else:
            new_global = current - 0.01

        new_diff = diff.with_global_difficulty(new_global).with_adaptation_tick(world.tick)

        # Determine assistance level – more assistance when difficulty is high and overload is high.
        assistance = 0.0
        if new_global > 0.7:
            assistance = min(1.0, (new_global - 0.7) * 2.0)
        if overload.overload_level > 0.6:
            assistance = max(assistance, (overload.overload_level - 0.6) * 2.0)
        new_diff = new_diff.with_assistance_level(assistance)

        # Emit events for direction changes
        if new_global > current:
            events.append(TimelineEvent(world.tick, "adaptive_difficulty_increased"))
        elif new_global < current:
            events.append(TimelineEvent(world.tick, "adaptive_difficulty_reduced"))
        if assistance > 0.0:
            events.append(TimelineEvent(world.tick, "assistance_level_adjusted"))

        new_world = world.with_difficulty_profile(new_diff)
        for ev in events:
            new_world = new_world.append_timeline(ev)
        return new_world
