from __future__ import annotations

"""Deterministic competency evolution engine.

Updates the ``OperatorCompetencyProfile`` based on execution quality, overload, semantic conflicts,
complication handling, strategic stability, recovery efficiency, and technical precision.
All changes are immutable and deterministic – no randomness.
"""

from typing import List


from scrubin.adaptive.competency import OperatorCompetencyProfile, CompetencyDomain
from scrubin.execution.state import TechnicalExecutionState
from scrubin.ontology.overload_state import OverloadState
from scrubin.ontology.attention_state import AttentionState
from scrubin.ontology.conflict_engine import ConflictEngine  # for conflict detection (deterministic)
from scrubin.ontology.strategic_engine import StrategicEngine  # placeholder for strategic stability
from scrubin.adaptive.competency import OperatorCompetencyProfile
from dataclasses import replace


class CompetencyEvolutionEngine:
    def __init__(self, rng) -> None:
        self.rng = rng  # retained for future tie‑breaks

    def evolve(self, world: "WorldState") -> "WorldState":
        # Retrieve current profiles and states
        comp_profile: OperatorCompetencyProfile = getattr(world, "operator_competency_profile", OperatorCompetencyProfile())
        tech: TechnicalExecutionState = getattr(world, "technical_execution_state", TechnicalExecutionState())
        overload: OverloadState = getattr(world, "overload_state", OverloadState())
        attention: AttentionState = getattr(world, "attention_state", AttentionState())
        # For deterministic conflict severity we just inspect the IntentGraph pending intents size
        # and use it as a proxy for semantic conflict density.
        pending_intents = getattr(world, "intent_graph", None)
        conflict_density = len(pending_intents.pending_intents()) if pending_intents else 0


from scrubin.core.events import TimelineEvent
        events: List[TimelineEvent] = []

        # Simple deterministic update rules per domain (example for a generic "general" domain)
        # In a real implementation each domain would have its own logic.
        updated_domains: List[CompetencyDomain] = []
        for domain in comp_profile.domains:
            # Execution quality influences skill level and confidence
            skill_inc = tech.execution_confidence * 0.02 - overload.overload_level * 0.01
            new_skill = max(0.0, min(1.0, domain.skill_level + skill_inc))
            # Confidence may drift with recent failures
            confidence_adj = -0.03 * len(domain.recent_failures) + 0.01 * tech.execution_confidence
            new_confidence = max(0.0, min(1.0, domain.confidence + confidence_adj))
            # Consistency improves with low overload and high attention stability
            consistency_inc = (1.0 - overload.overload_level) * 0.01 + (1.0 - attention.task_switch_penalty) * 0.005
            new_consistency = max(0.0, min(1.0, domain.consistency + consistency_inc))
            # Stress tolerance improves with successful maneuvers
            stress_inc = 0.005 * (1.0 - overload.overload_level)
            new_stress = max(0.0, min(1.0, domain.stress_tolerance + stress_inc))
            # Recovery efficiency improves with low overload and low technical fatigue
            recovery_inc = 0.004 * (1.0 - overload.overload_level) * (1.0 - tech.cumulative_technical_fatigue)
            new_recovery = max(0.0, min(1.0, domain.recovery_efficiency + recovery_inc))
            # Semantic understanding improves when conflict_density is low
            semantic_adj = -0.01 * conflict_density + 0.005
            new_semantic = max(0.0, min(1.0, domain.semantic_understanding + semantic_adj))
            # Technical precision improves with low force_application
            precision_adj = -0.02 * tech.force_application + 0.01
            new_precision = max(0.0, min(1.0, domain.technical_precision + precision_adj))
            # Decision quality improves with low overload and high attention load
            decision_adj = 0.01 * (1.0 - overload.overload_level) + 0.005 * (attention.current_load / max(1, attention.attention_capacity))
            new_decision = max(0.0, min(1.0, domain.decision_quality + decision_adj))
            # Complication management improves with lower inflammatory level (proxy via overload)
            comp_mgmt_adj = -0.01 * overload.overload_level
            new_comp_mgmt = max(0.0, min(1.0, domain.complication_management + comp_mgmt_adj))
            # Progression velocity increments based on overall learning (confidence + skill)
            prog_vel_inc = 0.005 * (new_confidence + new_skill)
            new_prog_vel = max(0.0, min(1.0, domain.progression_velocity + prog_vel_inc))

            updated = domain\
                .with_skill_level(new_skill)\
                .with_confidence(new_confidence)\
                .with_consistency(new_consistency)\
                .with_stress_tolerance(new_stress)\
                .with_recovery_efficiency(new_recovery)\
                .with_semantic_understanding(new_semantic)\
                .with_technical_precision(new_precision)\
                .with_decision_quality(new_decision)\
                .with_complication_management(new_comp_mgmt)\
                .with_progression_velocity(new_prog_vel)
            updated_domains.append(updated)

        # Aggregate overall metrics (simple deterministic averages)
        if updated_domains:
            avg_skill = sum(d.skill_level for d in updated_domains) / len(updated_domains)
            avg_conf = sum(d.confidence for d in updated_domains) / len(updated_domains)
            avg_consistency = sum(d.consistency for d in updated_domains) / len(updated_domains)
        else:
            avg_skill = avg_conf = avg_consistency = 0.0

        # Update the OperatorCompetencyProfile with new domains and aggregates
        new_profile = comp_profile\
            .with_domains(tuple(updated_domains))\
            .with_overall_competency(avg_skill)\
            .with_adaptability_score(min(1.0, comp_profile.adaptability_score + 0.001))\
            .with_overload_resilience(min(1.0, comp_profile.overload_resilience + (1.0 - overload.overload_level) * 0.002))\
            .with_strategic_flexibility(min(1.0, comp_profile.strategic_flexibility + 0.001))\
            .with_semantic_accuracy(min(1.0, comp_profile.semantic_accuracy + new_semantic * 0.001))\
            .with_technical_reliability(min(1.0, comp_profile.technical_reliability + new_precision * 0.001))\
            .with_longitudinal_growth(min(1.0, comp_profile.longitudinal_growth + 0.001))\
            .with_procedural_confidence(min(1.0, avg_conf))\
            .with_fatigue_resistance(min(1.0, comp_profile.fatigue_resistance + (1.0 - tech.cumulative_technical_fatigue) * 0.001))

        # Emit events based on thresholds
        if avg_skill > 0.7:
            events.append(TimelineEvent(world.tick, "competency_growth_detected"))
        if conflict_density > 3:
            events.append(TimelineEvent(world.tick, "procedural_stagnation_detected"))
        if len(tech.failed_maneuvers) > 0 and avg_skill < 0.4:
            events.append(TimelineEvent(world.tick, "brittle_expertise_detected"))
        if tech.execution_confidence > 0.9 and avg_conf < 0.5:
            events.append(TimelineEvent(world.tick, "confidence_misalibration_detected"))
        if avg_skill > comp_profile.overall_competency:
            events.append(TimelineEvent(world.tick, "semantic_mastery_improving"))
        if overload.overload_level < comp_profile.overload_resilience:
            events.append(TimelineEvent(world.tick, "overload_resilience_improving"))

        new_world = world.with_operator_competency_profile(new_profile)
        for ev in events:
            new_world = new_world.append_timeline(ev)
        return new_world
