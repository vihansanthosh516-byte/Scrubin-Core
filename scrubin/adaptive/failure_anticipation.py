from __future__ import annotations

"""Deterministic failure anticipation engine.

Predicts imminent procedural and physiological failures based on competency,
overload, consequence memory, and current system state.
"""

from dataclasses import dataclass, replace
from typing import List, Tuple


from scrubin.adaptive.competency import OperatorCompetencyProfile
from scrubin.execution.state import TechnicalExecutionState
from scrubin.ontology.overload_state import OverloadState
from scrubin.ontology.attention_state import AttentionState
from scrubin.ontology.intent_graph import IntentGraph
from scrubin.memory.consequence_memory import ConsequenceMemory


@dataclass(frozen=True)
class FailurePrediction:
    prediction_id: str
    predicted_failure_type: str
    severity: float = 0.0  # 0‑1
    confidence: float = 0.0  # 0‑1
    contributing_domains: Tuple[str, ...] = field(default_factory=tuple)
    contributing_events: Tuple[str, ...] = field(default_factory=tuple)
    projected_tick_horizon: int = 0
    mitigation_strategy: str = ""

    def with_severity(self, v: float) -> "FailurePrediction":
        return replace(self, severity=max(0.0, min(1.0, v)))

    def with_confidence(self, v: float) -> "FailurePrediction":
        return replace(self, confidence=max(0.0, min(1.0, v)))

    def with_projected_tick_horizon(self, ticks: int) -> "FailurePrediction":
        return replace(self, projected_tick_horizon=ticks)

    def with_mitigation_strategy(self, strat: str) -> "FailurePrediction":
        return replace(self, mitigation_strategy=strat)


class FailureAnticipationEngine:
    """Deterministically predict failures and emit timeline warnings."""

    def __init__(self, rng) -> None:
        self.rng = rng  # retained for future tie‑breaks

    def analyze(self, world: "WorldState") -> "WorldState":
        comp: OperatorCompetencyProfile = getattr(world, "operator_competency_profile", OperatorCompetencyProfile())
        tech: TechnicalExecutionState = getattr(world, "technical_execution_state", TechnicalExecutionState())
        overload: OverloadState = getattr(world, "overload_state", OverloadState())
        attention: AttentionState = getattr(world, "attention_state", AttentionState())
        intent_graph: IntentGraph = getattr(world, "intent_graph", IntentGraph())
        consequence_mem = getattr(world, "consequence_memory", ConsequenceMemory())
        from scrubin.core.events import TimelineEvent
        events: List[TimelineEvent] = []

        # Simple deterministic criteria for each failure type
        # 1. Overload collapse – when overload > 0.7 and competency overload_resilience low
        if overload.overload_level > 0.7 and comp.overload_resilience < 0.4:
            pred = FailurePrediction(
                prediction_id=f"overload_{world.tick}",
                predicted_failure_type="overload_collapse",
                severity=0.8,
                confidence=0.9,
                contributing_domains=("overload_resilience",),
                contributing_events=("overload",),
                projected_tick_horizon=world.tick + 5,
                mitigation_strategy="reduce workload, increase assistance",
            )
            events.append(TimelineEvent(world.tick, "overload_failure_predicted"))
            events.append(TimelineEvent(world.tick, "predicted_failure_escalating"))

        # 2. Hemorrhage escalation – simple proxy via recent failed maneuvers count
        if len(tech.failed_maneuvers) > 2:
            pred = FailurePrediction(
                prediction_id=f"hemorrhage_{world.tick}",
                predicted_failure_type="hemorrhage_escalation",
                severity=0.7,
                confidence=0.85,
                contributing_domains=("technical_precision",),
                contributing_events=tech.failed_maneuvers,
                projected_tick_horizon=world.tick + 3,
                mitigation_strategy="improve visualization, reduce force",
            )
            events.append(TimelineEvent(world.tick, "procedural_collapse_risk_detected"))
            events.append(TimelineEvent(world.tick, "predicted_failure_escalating"))

        # 3. Semantic fixation loop – when attention load exceeds capacity repeatedly
        if attention.current_load > attention.overload_threshold and comp.semantic_accuracy < 0.5:
            pred = FailurePrediction(
                prediction_id=f"semantic_fix_{world.tick}",
                predicted_failure_type="semantic_fixation",
                severity=0.6,
                confidence=0.8,
                contributing_domains=("semantic_accuracy",),
                contributing_events=("attention_overload",),
                projected_tick_horizon=world.tick + 4,
                mitigation_strategy="pause, review semantic context",
            )
            events.append(TimelineEvent(world.tick, "semantic_fixation_risk_detected"))
            events.append(TimelineEvent(world.tick, "predicted_failure_escalating"))

        # 4. Recovery destabilization – when recovery debt high and overload high
        # Use a deterministic proxy via consequence memory (overload periods)
        if len(consequence_mem.overload_periods) > 5 and overload.overload_level > 0.5:
            pred = FailurePrediction(
                prediction_id=f"recovery_destab_{world.tick}",
                predicted_failure_type="recovery_destabilization",
                severity=0.75,
                confidence=0.88,
                contributing_domains=("recovery_debt",),
                contributing_events=consequence_mem.overload_periods,
                projected_tick_horizon=world.tick + 6,
                mitigation_strategy="reduce workload, increase assistance",
            )
            events.append(TimelineEvent(world.tick, "recovery_destabilization_predicted"))
            events.append(TimelineEvent(world.tick, "predicted_failure_escalating"))

        new_world = world
        for ev in events:
            new_world = new_world.append_timeline(ev)
        return new_world
