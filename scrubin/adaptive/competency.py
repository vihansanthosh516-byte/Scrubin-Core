from __future__ import annotations

"""Operator competency model – immutable, deterministic, ontology‑aware."""

from dataclasses import dataclass, field, replace
from typing import Tuple


@dataclass(frozen=True)
class CompetencyDomain:
    """Fine‑grained competency domain metrics.

    All values are clamped to the range 0.0‑1.0 where applicable.
    """

    domain_id: str
    skill_level: float = 0.0
    confidence: float = 0.0
    consistency: float = 0.0
    stress_tolerance: float = 0.0
    recovery_efficiency: float = 0.0
    semantic_understanding: float = 0.0
    technical_precision: float = 0.0
    decision_quality: float = 0.0
    complication_management: float = 0.0
    progression_velocity: float = 0.0
    recent_failures: Tuple[str, ...] = field(default_factory=tuple)

    # -----------------------------------------------------------------
    # Deterministic ``with_*`` helpers – each returns a new immutable instance.
    # -----------------------------------------------------------------
    def with_skill_level(self, v: float) -> "CompetencyDomain":
        return replace(self, skill_level=max(0.0, min(1.0, v)))

    def with_confidence(self, v: float) -> "CompetencyDomain":
        return replace(self, confidence=max(0.0, min(1.0, v)))

    def with_consistency(self, v: float) -> "CompetencyDomain":
        return replace(self, consistency=max(0.0, min(1.0, v)))

    def with_stress_tolerance(self, v: float) -> "CompetencyDomain":
        return replace(self, stress_tolerance=max(0.0, min(1.0, v)))

    def with_recovery_efficiency(self, v: float) -> "CompetencyDomain":
        return replace(self, recovery_efficiency=max(0.0, min(1.0, v)))

    def with_semantic_understanding(self, v: float) -> "CompetencyDomain":
        return replace(self, semantic_understanding=max(0.0, min(1.0, v)))

    def with_technical_precision(self, v: float) -> "CompetencyDomain":
        return replace(self, technical_precision=max(0.0, min(1.0, v)))

    def with_decision_quality(self, v: float) -> "CompetencyDomain":
        return replace(self, decision_quality=max(0.0, min(1.0, v)))

    def with_complication_management(self, v: float) -> "CompetencyDomain":
        return replace(self, complication_management=max(0.0, min(1.0, v)))

    def with_progression_velocity(self, v: float) -> "CompetencyDomain":
        return replace(self, progression_velocity=max(0.0, min(1.0, v)))

    def add_recent_failure(self, failure_id: str) -> "CompetencyDomain":
        return replace(self, recent_failures=self.recent_failures + (failure_id,))


@dataclass(frozen=True)
class OperatorCompetencyProfile:
    """Aggregated competency profile for a single operator.

    ``domains`` are kept sorted by ``domain_id`` for deterministic ordering.
    """

    operator_id: str = ""
    domains: Tuple[CompetencyDomain, ...] = field(default_factory=tuple)
    overall_competency: float = 0.0
    adaptability_score: float = 0.0
    overload_resilience: float = 0.0
    strategic_flexibility: float = 0.0
    semantic_accuracy: float = 0.0
    technical_reliability: float = 0.0
    longitudinal_growth: float = 0.0
    procedural_confidence: float = 0.0
    fatigue_resistance: float = 0.0
    curriculum_stage: str = ""
    competency_tick: int = 0

    # -----------------------------------------------------------------
    # Helper methods – deterministic and immutable.
    # -----------------------------------------------------------------
    def get_domain(self, domain_id: str) -> CompetencyDomain | None:
        for d in self.domains:
            if d.domain_id == domain_id:
                return d
        return None

    def _sorted_domains(self, domains: Tuple[CompetencyDomain, ...]) -> Tuple[CompetencyDomain, ...]:
        return tuple(sorted(domains, key=lambda d: d.domain_id))

    def with_domain(self, updated: CompetencyDomain) -> "OperatorCompetencyProfile":
        filtered = tuple(d for d in self.domains if d.domain_id != updated.domain_id)
        new_domains = self._sorted_domains(filtered + (updated,))
        return replace(self, domains=new_domains)

    def with_domains(self, domains: Tuple[CompetencyDomain, ...]) -> "OperatorCompetencyProfile":
        return replace(self, domains=self._sorted_domains(domains))

    def with_overall_competency(self, v: float) -> "OperatorCompetencyProfile":
        return replace(self, overall_competency=max(0.0, min(1.0, v)))

    def with_adaptability_score(self, v: float) -> "OperatorCompetencyProfile":
        return replace(self, adaptability_score=max(0.0, min(1.0, v)))

    def with_overload_resilience(self, v: float) -> "OperatorCompetencyProfile":
        return replace(self, overload_resilience=max(0.0, min(1.0, v)))

    def with_strategic_flexibility(self, v: float) -> "OperatorCompetencyProfile":
        return replace(self, strategic_flexibility=max(0.0, min(1.0, v)))

    def with_semantic_accuracy(self, v: float) -> "OperatorCompetencyProfile":
        return replace(self, semantic_accuracy=max(0.0, min(1.0, v)))

    def with_technical_reliability(self, v: float) -> "OperatorCompetencyProfile":
        return replace(self, technical_reliability=max(0.0, min(1.0, v)))

    def with_longitudinal_growth(self, v: float) -> "OperatorCompetencyProfile":
        return replace(self, longitudinal_growth=max(0.0, min(1.0, v)))

    def with_procedural_confidence(self, v: float) -> "OperatorCompetencyProfile":
        return replace(self, procedural_confidence=max(0.0, min(1.0, v)))

    def with_fatigue_resistance(self, v: float) -> "OperatorCompetencyProfile":
        return replace(self, fatigue_resistance=max(0.0, min(1.0, v)))

    def with_curriculum_stage(self, stage: str) -> "OperatorCompetencyProfile":
        return replace(self, curriculum_stage=stage)

    def with_tick(self, tick: int) -> "OperatorCompetencyProfile":
        return replace(self, competency_tick=tick)
