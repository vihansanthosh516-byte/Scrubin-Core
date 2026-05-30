from __future__ import annotations

"""Deterministic performance analytics engine – longitudinal analysis of operator metrics."""

from dataclasses import dataclass, field, replace
from typing import List, Tuple


from scrubin.adaptive.competency import OperatorCompetencyProfile
from scrubin.execution.state import TechnicalExecutionState
from scrubin.ontology.overload_state import OverloadState
from scrubin.ontology.attention_state import AttentionState


@dataclass(frozen=True)
class PerformanceSnapshot:
    tick: int
    competency_score: float = 0.0
    overload_score: float = 0.0
    semantic_accuracy: float = 0.0
    strategic_stability: float = 0.0
    execution_precision: float = 0.0
    recovery_quality: float = 0.0
    contamination_control: float = 0.0
    workflow_efficiency: float = 0.0
    complication_management: float = 0.0
    longitudinal_risk: float = 0.0

    # deterministic with_* helpers
    def with_competency_score(self, v: float) -> "PerformanceSnapshot":
        return replace(self, competency_score=max(0.0, min(1.0, v)))

    def with_overload_score(self, v: float) -> "PerformanceSnapshot":
        return replace(self, overload_score=max(0.0, min(1.0, v)))

    def with_semantic_accuracy(self, v: float) -> "PerformanceSnapshot":
        return replace(self, semantic_accuracy=max(0.0, min(1.0, v)))

    def with_strategic_stability(self, v: float) -> "PerformanceSnapshot":
        return replace(self, strategic_stability=max(0.0, min(1.0, v)))

    def with_execution_precision(self, v: float) -> "PerformanceSnapshot":
        return replace(self, execution_precision=max(0.0, min(1.0, v)))

    def with_recovery_quality(self, v: float) -> "PerformanceSnapshot":
        return replace(self, recovery_quality=max(0.0, min(1.0, v)))

    def with_contamination_control(self, v: float) -> "PerformanceSnapshot":
        return replace(self, contamination_control=max(0.0, min(1.0, v)))

    def with_workflow_efficiency(self, v: float) -> "PerformanceSnapshot":
        return replace(self, workflow_efficiency=max(0.0, min(1.0, v)))

    def with_complication_management(self, v: float) -> "PerformanceSnapshot":
        return replace(self, complication_management=max(0.0, min(1.0, v)))

    def with_longitudinal_risk(self, v: float) -> "PerformanceSnapshot":
        return replace(self, longitudinal_risk=max(0.0, min(1.0, v)))


@dataclass(frozen=True)
class PerformanceAnalytics:
    snapshots: Tuple[PerformanceSnapshot, ...] = field(default_factory=tuple)
    rolling_competency: float = 0.0
    rolling_precision: float = 0.0
    rolling_resilience: float = 0.0
    longitudinal_improvement: float = 0.0
    volatility_score: float = 0.0
    burnout_risk: float = 0.0
    plateau_risk: float = 0.0

    # deterministic helpers
    def add_snapshot(self, snap: PerformanceSnapshot) -> "PerformanceAnalytics":
        new_snaps = self.snapshots + (snap,)
        return replace(self, snapshots=new_snaps)

    def with_rolling_competency(self, v: float) -> "PerformanceAnalytics":
        return replace(self, rolling_competency=max(0.0, min(1.0, v)))

    def with_rolling_precision(self, v: float) -> "PerformanceAnalytics":
        return replace(self, rolling_precision=max(0.0, min(1.0, v)))

    def with_rolling_resilience(self, v: float) -> "PerformanceAnalytics":
        return replace(self, rolling_resilience=max(0.0, min(1.0, v)))

    def with_longitudinal_improvement(self, v: float) -> "PerformanceAnalytics":
        return replace(self, longitudinal_improvement=max(0.0, min(1.0, v)))

    def with_volatility_score(self, v: float) -> "PerformanceAnalytics":
        return replace(self, volatility_score=max(0.0, min(1.0, v)))

    def with_burnout_risk(self, v: float) -> "PerformanceAnalytics":
        return replace(self, burnout_risk=max(0.0, min(1.0, v)))

    def with_plateau_risk(self, v: float) -> "PerformanceAnalytics":
        return replace(self, plateau_risk=max(0.0, min(1.0, v)))


class AnalyticsEngine:
    """Deterministically compute longitudinal analytics and emit events."""

    def __init__(self, rng) -> None:
        self.rng = rng  # retained for future tie‑breaks

    def analyze(self, world: "WorldState") -> "WorldState":
        comp: OperatorCompetencyProfile = getattr(world, "operator_competency_profile", OperatorCompetencyProfile())
        tech: TechnicalExecutionState = getattr(world, "technical_execution_state", TechnicalExecutionState())
        overload: OverloadState = getattr(world, "overload_state", OverloadState())
        attention: AttentionState = getattr(world, "attention_state", AttentionState())
        analytics: PerformanceAnalytics = getattr(world, "performance_analytics", PerformanceAnalytics())
        from scrubin.core.events import TimelineEvent
        events: List[TimelineEvent] = []

        # Build a snapshot – deterministic derivations
        snap = PerformanceSnapshot(
            tick=world.tick,
            competency_score=comp.overall_competency,
            overload_score=overload.overload_level,
            semantic_accuracy=comp.semantic_accuracy,
            strategic_stability=comp.strategic_flexibility,
            execution_precision=tech.precision,
            recovery_quality=1.0 - comp.overload_resilience,  # placeholder metric
            contamination_control=1.0 - tech.current_risk_level,
            workflow_efficiency=1.0 - tech.unsafe_motion_count / max(1, tech.execution_latency + 1),
            complication_management=comp.complication_management,
            longitudinal_risk=tech.micro_error_accumulation,
        )
        analytics = analytics.add_snapshot(snap)

        # Compute rolling averages (deterministic window of last 5 snapshots)
        recent = analytics.snapshots[-5:]
        if recent:
            def avg(attr: str) -> float:
                return sum(getattr(s, attr) for s in recent) / len(recent)
            analytics = analytics\
                .with_rolling_competency(avg("competency_score"))\
                .with_rolling_precision(avg("execution_precision"))\
                .with_rolling_resilience(avg("overload_score"))
        # Detect burnout – high overload and low competency over window
        if overload.overload_level > 0.7 and comp.overall_competency < 0.4:
            analytics = analytics.with_burnout_risk(min(1.0, analytics.burnout_risk + 0.05))
            events.append(TimelineEvent(world.tick, "burnout_risk_increasing"))
        else:
            analytics = analytics.with_burnout_risk(max(0.0, analytics.burnout_risk - 0.02))

        # Detect plateau – rolling competency change small over window
        if len(recent) >= 5:
            first = recent[0].competency_score
            last = recent[-1].competency_score
            if abs(last - first) < 0.02:
                analytics = analytics.with_plateau_risk(min(1.0, analytics.plateau_risk + 0.04))
                events.append(TimelineEvent(world.tick, "performance_plateau_detected"))
            else:
                analytics = analytics.with_plateau_risk(max(0.0, analytics.plateau_risk - 0.03))

        # Detect resilience growth – improvement in overload score over window
        if len(recent) >= 5:
            first_over = recent[0].overload_score
            last_over = recent[-1].overload_score
            if last_over < first_over - 0.05:
                analytics = analytics.with_rolling_resilience(min(1.0, analytics.rolling_resilience + 0.03))
                events.append(TimelineEvent(world.tick, "resilience_growth_detected"))
            else:
                analytics = analytics.with_rolling_resilience(max(0.0, analytics.rolling_resilience - 0.02))

        # Detect semantic consistency improvement – semantic_accuracy trend
        if len(recent) >= 5:
            first_sem = recent[0].semantic_accuracy
            last_sem = recent[-1].semantic_accuracy
            if last_sem > first_sem + 0.03:
                events.append(TimelineEvent(world.tick, "semantic_consistency_improving"))
                analytics = analytics.with_longitudinal_improvement(min(1.0, analytics.longitudinal_improvement + 0.04))
            else:
                analytics = analytics.with_longitudinal_improvement(max(0.0, analytics.longitudinal_improvement - 0.02))

        new_world = world.with_performance_analytics(analytics)
        for ev in events:
            new_world = new_world.append_timeline(ev)
        return new_world
